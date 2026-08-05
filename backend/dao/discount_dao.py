from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import Discount
from schemas.coupon_schemas import DiscountIn


async def list_discounts(db: AsyncSession) -> list[Discount]:
    result = await db.execute(select(Discount))
    return result.scalars().all()


async def get_active_discounts(db: AsyncSession) -> list[Discount]:
    """현재 활성화된 할인 목록 (주문 계산에 사용)"""
    result = await db.execute(select(Discount).where(Discount.is_active == True))
    return result.scalars().all()


async def create_discount(db: AsyncSession, data: DiscountIn) -> Discount:
    discount = Discount(**data.model_dump())
    db.add(discount)
    await db.flush()
    return discount


async def toggle_discount(db: AsyncSession, discount_id: str) -> Discount | None:
    discount = await db.get(Discount, discount_id)
    if discount is None:
        return None
    discount.is_active = not discount.is_active
    await db.flush()
    return discount


async def delete_discount(db: AsyncSession, discount_id: str) -> bool:
    discount = await db.get(Discount, discount_id)
    if discount is None:
        return False
    await db.delete(discount)
    await db.flush()
    return True
