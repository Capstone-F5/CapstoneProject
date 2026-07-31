from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.core.models import Coupon, UserCoupon, User
from backend.schemas.coupon_schemas import CouponIn


async def list_coupons(db: AsyncSession) -> list[Coupon]:
    result = await db.execute(select(Coupon))
    return result.scalars().all()


async def create_coupon(db: AsyncSession, data: CouponIn) -> Coupon:
    coupon = Coupon(**data.model_dump())
    db.add(coupon)
    await db.flush()
    return coupon


async def toggle_coupon(db: AsyncSession, coupon_id: str) -> Coupon | None:
    coupon = await db.get(Coupon, coupon_id)
    if coupon is None:
        return None
    coupon.is_active = not coupon.is_active
    await db.flush()
    return coupon


async def delete_coupon(db: AsyncSession, coupon_id: str) -> Coupon | None:
    coupon = await db.get(Coupon, coupon_id)
    if coupon is None:
        return None
    count_result = await db.execute(
        select(func.count()).where(UserCoupon.coupon_id == coupon_id)
    )
    if count_result.scalar() > 0:
        coupon.is_active = False
        await db.flush()
        raise ValueError("이미 발급된 쿠폰이 있어 삭제할 수 없습니다. 비활성화 처리했습니다.")
    await db.delete(coupon)
    await db.flush()
    return coupon


async def issue_coupon_to_user(db: AsyncSession, coupon_id: str, phone: str) -> UserCoupon:
    result = await db.execute(select(User).where(User.phone_number == phone))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("해당 전화번호의 회원을 찾을 수 없습니다.")

    user_coupon = UserCoupon(user_id=user.id, coupon_id=coupon_id)
    db.add(user_coupon)
    await db.flush()
    return user_coupon
