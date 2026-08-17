from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.security import get_current_admin
from dao import discount_dao
from schemas.coupon_schemas import DiscountIn, DiscountOut
from ai_modules.llm.rag import invalidate_cache

router = APIRouter(
    prefix="/api/admin/discounts",
    tags=["admin-discounts"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("", response_model=list[DiscountOut])
async def get_discounts(db: AsyncSession = Depends(get_session)):
    return await discount_dao.list_discounts(db)


@router.post("", response_model=DiscountOut)
async def create_discount(body: DiscountIn, db: AsyncSession = Depends(get_session)):
    # target_type 검증 규칙 적용
    if body.target_type == "MENU" and not body.menu_item_id:
        raise HTTPException(status_code=400, detail="MENU 할인 시 menu_item_id는 필수입니다.")
    if body.target_type == "CATEGORY" and not body.category_id:
        raise HTTPException(status_code=400, detail="CATEGORY 할인 시 category_id는 필수입니다.")

    discount = await discount_dao.create_discount(db, body)
    await db.commit()
    await db.refresh(discount)
    invalidate_cache()
    return discount


@router.patch("/{id}/toggle", response_model=DiscountOut)
async def toggle_discount(id: str, db: AsyncSession = Depends(get_session)):
    discount = await discount_dao.toggle_discount(db, id)
    if discount is None:
        raise HTTPException(status_code=404, detail="할인을 찾을 수 없습니다.")
    await db.commit()
    await db.refresh(discount)
    invalidate_cache()
    return discount


@router.delete("/{id}")
async def delete_discount(id: str, db: AsyncSession = Depends(get_session)):
    ok = await discount_dao.delete_discount(db, id)
    if not ok:
        raise HTTPException(status_code=404, detail="할인을 찾을 수 없습니다.")
    await db.commit()
    invalidate_cache()
    return {"ok": True}
