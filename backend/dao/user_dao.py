from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import User, Membership, UserCoupon, Coupon

async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(
        select(User).where(User.phone_number == phone)
    )
    return result.scalar_one_or_none()

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