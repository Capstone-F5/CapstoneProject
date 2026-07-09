from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_session
from dao.user_dao import get_user_by_phone, get_membership, get_unused_coupons
from schemas.user_schemas import UserPointsOut, CouponOut

router = APIRouter(prefix="/api/user", tags=["user"])

@router.get("/points/{phone}", response_model=UserPointsOut)
async def get_user_points(phone: str, db: AsyncSession = Depends(get_session)):
    user = await get_user_by_phone(db, phone)
    if user is None:
        raise HTTPException(status_code=404, detail="등록된 회원이 아닙니다")
    membership = await get_membership(db, user.id)
    return UserPointsOut(
        user_id=user.id,
        phone_number=user.phone_number,
        current_points=user.current_points,
        tier=membership.tier if membership else None,
    )

@router.get("/{user_id}/coupons", response_model=list[CouponOut])
async def get_user_coupons(user_id: str, db: AsyncSession = Depends(get_session)):
    user_coupons = await get_unused_coupons(db, user_id)
    result = []
    for uc in user_coupons:
        result.append(CouponOut(
            user_coupon_id=uc.id,
            coupon_code=uc.coupon.code if uc.coupon else "",
            discount_type=uc.coupon.discount_type if uc.coupon else "",
            discount_value=float(uc.coupon.discount_value) if uc.coupon else 0,
            min_order_amount=float(uc.coupon.min_order_amount) if uc.coupon else 0,
            is_used=uc.is_used,
            valid_until=str(uc.coupon.valid_until) if uc.coupon and uc.coupon.valid_until else None,
        ))
    return result