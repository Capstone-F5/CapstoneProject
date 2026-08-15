"""키오스크가 인증 없이 읽는 현재 적용 가능 할인 API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from dao import discount_dao
from schemas.coupon_schemas import DiscountOut

router = APIRouter(prefix="/api/discounts", tags=["discounts"])


@router.get("/active", response_model=list[DiscountOut])
async def get_active_discounts(db: AsyncSession = Depends(get_session)):
    """비회원 키오스크에 적용되는 오늘의 ALL/MENU/CATEGORY 할인만 반환한다."""
    discounts = await discount_dao.get_active_discounts(db)
    return [discount for discount in discounts if discount.applicable_tier == "ALL"]
