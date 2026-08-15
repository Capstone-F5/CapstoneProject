from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from core.models import Discount
from schemas.coupon_schemas import DiscountIn


async def list_discounts(db: AsyncSession) -> list[Discount]:
    result = await db.execute(select(Discount))
    return result.scalars().all()


async def get_active_discounts(db: AsyncSession, *, today: date | None = None) -> list[Discount]:
    """오늘 적용 가능한 활성 할인 목록 (주문 계산과 공개 조회에 공통 사용)."""
    today = today or date.today()
    result = await db.execute(
        select(Discount).where(
            Discount.is_active.is_(True),
            or_(Discount.valid_from.is_(None), Discount.valid_from <= today),
            or_(Discount.valid_until.is_(None), Discount.valid_until >= today),
        )
    )
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
