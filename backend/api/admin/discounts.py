from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.dao import discount_dao
from backend.schemas.coupon_schemas import DiscountIn, DiscountOut

router = APIRouter(prefix="/api/admin/discounts", tags=["admin-discounts"])


@router.get("", response_model=list[DiscountOut])
def get_discounts(db: Session = Depends(get_db)):
    return discount_dao.list_discounts(db)


@router.post("", response_model=DiscountOut)
def create_discount(body: DiscountIn, db: Session = Depends(get_db)):
    # target_type 검증 규칙 적용
    if body.target_type == "MENU" and not body.menu_item_id:
        raise HTTPException(status_code=400, detail="MENU 할인 시 menu_item_id는 필수입니다.")
    if body.target_type == "CATEGORY" and not body.category_id:
        raise HTTPException(status_code=400, detail="CATEGORY 할인 시 category_id는 필수입니다.")

    discount = discount_dao.create_discount(db, body)
    db.commit()
    db.refresh(discount)
    return discount
