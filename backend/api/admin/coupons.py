from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.core.db import get_db
from backend.dao import coupon_dao
from backend.schemas.coupon_schemas import CouponIn, CouponOut, UserCouponOut

router = APIRouter(prefix="/api/admin/coupons", tags=["admin-coupons"])


class IssueReq(BaseModel):
    phone: str


@router.get("", response_model=list[CouponOut])
def get_coupons(db: Session = Depends(get_db)):
    return coupon_dao.list_coupons(db)


@router.post("", response_model=CouponOut)
def create_coupon(body: CouponIn, db: Session = Depends(get_db)):
    coupon = coupon_dao.create_coupon(db, body)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.post("/{id}/issue", response_model=UserCouponOut)
def issue_coupon(id: str, body: IssueReq, db: Session = Depends(get_db)):
    try:
        user_coupon = coupon_dao.issue_coupon_to_user(db, id, body.phone)
        db.commit()
        db.refresh(user_coupon)
        return UserCouponOut(
            user_coupon_id=user_coupon.id,
            user_id=user_coupon.user_id,
            coupon_id=user_coupon.coupon_id,
            issued_at=user_coupon.issued_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    