import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import User, Membership, UserCoupon, Coupon, PointEarnLog

logger = logging.getLogger(__name__)

POINTS_EXPIRE_AFTER_DAYS = 30

async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(
        select(User).where(User.phone_number == phone)
    )
    return result.scalar_one_or_none()


async def create_guest_user(db: AsyncSession, phone: str) -> User:
    """전화번호로 포인트 적립을 신청했지만 회원 레코드가 없는 경우 자동 가입시킨다."""
    user = User(phone_number=phone, is_guest=False, current_points=0)
    db.add(user)
    await db.flush()
    return user

async def get_membership(db: AsyncSession, user_id: str) -> Membership | None:
    result = await db.execute(
        select(Membership).where(Membership.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def get_unused_coupons(db: AsyncSession, user_id: str) -> list[UserCoupon]:
    result = await db.execute(
        select(UserCoupon)
        .where(UserCoupon.user_id == user_id)
        .where(UserCoupon.is_used == False)
    )
    return result.scalars().all()

async def get_coupon_by_code(db: AsyncSession, code: str) -> Coupon | None:
    result = await db.execute(
        select(Coupon)
        .where(Coupon.code == code)
        .where(Coupon.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_user_coupon(db: AsyncSession, user_id: str, coupon_id: str) -> UserCoupon | None:
    result = await db.execute(
        select(UserCoupon)
        .where(UserCoupon.user_id == user_id)
        .where(UserCoupon.coupon_id == coupon_id)
        .where(UserCoupon.is_used == False)
    )
    return result.scalar_one_or_none()


# --- 포인트 적립/만료 -------------------------------------------------------

async def create_point_earn_log(
    db: AsyncSession, user_id: str, order_id: str | None, points: int
) -> PointEarnLog | None:
    """적립 시 원장에 한 건 남긴다 — 이 적립분이 나중에 30일 경과로 만료될 때 기준이 된다."""
    if points <= 0:
        return None
    log = PointEarnLog(user_id=user_id, order_id=order_id, points=points, remaining=points)
    db.add(log)
    await db.flush()
    return log


async def consume_points_fifo(db: AsyncSession, user_id: str, amount: int) -> None:
    """포인트 사용 시 가장 오래된 적립분부터 차감(FIFO)한다 — 만료 계산의 기준(remaining)을 정확히 유지하기 위함."""
    if amount <= 0:
        return
    result = await db.execute(
        select(PointEarnLog)
        .where(PointEarnLog.user_id == user_id)
        .where(PointEarnLog.remaining > 0)
        .order_by(PointEarnLog.earned_at.asc())
    )
    remaining_to_consume = amount
    for log in result.scalars().all():
        if remaining_to_consume <= 0:
            break
        take = min(log.remaining, remaining_to_consume)
        log.remaining -= take
        remaining_to_consume -= take
    await db.flush()


async def expire_old_points(db: AsyncSession, user: User) -> int:
    """적립 후 30일이 지난 미사용 포인트를 만료 처리하고, 실제로 만료된 총량을 반환한다.

    current_points 는 여전히 총합 카운터로 유지하되, 여기서 만료분만큼 차감한다.
    """
    cutoff = datetime.utcnow() - timedelta(days=POINTS_EXPIRE_AFTER_DAYS)
    result = await db.execute(
        select(PointEarnLog)
        .where(PointEarnLog.user_id == user.id)
        .where(PointEarnLog.remaining > 0)
        .where(PointEarnLog.earned_at <= cutoff)
        .where(PointEarnLog.expired_at.is_(None))
    )
    expired_total = 0
    for log in result.scalars().all():
        expired_total += log.remaining
        log.remaining = 0
        log.expired_at = datetime.utcnow()

    if expired_total:
        user.current_points = max(0, user.current_points - expired_total)
        await db.flush()
        logger.info("points expired: user_id=%s amount=%s", user.id, expired_total)

    return expired_total


# --- 관리자용 (Module G) -----------------------------------------------------

async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def search_users(db: AsyncSession, phone: str | None = None) -> list[User]:
    query = select(User).order_by(User.created_at.desc())
    if phone:
        query = query.where(User.phone_number.contains(phone))
    result = await db.execute(query)
    return result.scalars().all()


async def get_all_user_coupons(db: AsyncSession, user_id: str) -> list[UserCoupon]:
    result = await db.execute(
        select(UserCoupon).where(UserCoupon.user_id == user_id)
    )
    return result.scalars().all()


async def adjust_points(db: AsyncSession, user_id: str, delta: int, reason: str) -> User | None:
    """포인트 수동 증감. reason은 서버 로그에 남긴다."""
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None
    user.current_points += delta
    await db.flush()
    logger.info(
        "admin points adjustment: user_id=%s delta=%s reason=%s new_balance=%s",
        user_id, delta, reason, user.current_points,
    )
    return user