import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.models import User, Membership, UserCoupon, Coupon, PointEarnLog

logger = logging.getLogger(__name__)

POINTS_EXPIRE_AFTER_DAYS = 30

async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(
        select(User).where(User.phone_number == phone)
    )
    return result.scalar_one_or_none()


async def create_guest_user(db: AsyncSession, phone: str) -> User:
    """전화번호로 포인트 적립만 요청했을 뿐 정식 회원가입은 하지 않은 경우.

    ★ is_guest=True 로 남긴다 — 전화번호를 한 번 입력했다고 회원가입이 되는 것은 아니다.
    이 레코드는 포인트를 전화번호 기준으로 누적 추적하기 위한 것일 뿐, 실제 회원 여부는
    register_user()로 별도 회원가입을 마쳐야 is_guest=False 로 바뀐다.
    """
    user = User(phone_number=phone, is_guest=True, current_points=0)
    db.add(user)
    await db.flush()
    return user


async def register_user(db: AsyncSession, phone: str, name: str | None) -> tuple[User, bool]:
    """정식 회원가입. 이미 포인트 추적용으로 생성된 비회원(is_guest=True) 레코드가 있으면
    그 레코드를 정식 회원으로 전환(포인트 유지)하고, 없으면 새로 만든다.

    Returns:
        (user, already_member): already_member 는 가입 시도 전에 이미 정식 회원이었는지 여부.
    """
    user = await get_user_by_phone(db, phone)
    if user is None:
        user = User(phone_number=phone, name=name, is_guest=False, current_points=0)
        db.add(user)
        await db.flush()
        return user, False

    already_member = not user.is_guest
    user.is_guest = False
    if name:
        user.name = name
    await db.flush()
    return user, already_member

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


async def adjust_points(db: AsyncSession, user_id: str, delta: int, reason: str = "") -> User | None:
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

# --- Module C: 쿠폰 관련 DAO ---

async def get_user_coupon_by_code(db: AsyncSession, user_id: str, code: str) -> UserCoupon | None:
    """쿠폰 코드로 미사용 유저 쿠폰 조회"""
    result = await db.execute(
        select(UserCoupon)
        .join(Coupon, UserCoupon.coupon_id == Coupon.id)
        .where(
            UserCoupon.user_id == user_id,
            Coupon.code == code,
            UserCoupon.is_used == False,
        )
        .options(selectinload(UserCoupon.coupon))
    )
    return result.scalar_one_or_none()


async def mark_coupon_used(db: AsyncSession, user_coupon_id: str) -> None:
    """쿠폰 사용 완료 처리. is_used=True, used_at=now(), coupons.used_count += 1."""
    user_coupon = await db.get(UserCoupon, user_coupon_id)
    if user_coupon:
        user_coupon.is_used = True
        user_coupon.used_at = datetime.utcnow()
        coupon = await db.get(Coupon, user_coupon.coupon_id)
        if coupon:
            coupon.used_count += 1
        await db.flush()


async def restore_coupon(db: AsyncSession, user_coupon_id: str) -> None:
    """환불 시 쿠폰 복구. mark_coupon_used의 반대 동작."""
    user_coupon = await db.get(UserCoupon, user_coupon_id)
    if user_coupon:
        user_coupon.is_used = False
        user_coupon.used_at = None
        coupon = await db.get(Coupon, user_coupon.coupon_id)
        if coupon:
            coupon.used_count -= 1
        await db.flush()