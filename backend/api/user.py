import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_session
from dao.user_dao import get_user_by_phone, get_membership, get_unused_coupons, expire_old_points, register_user
from schemas.user_schemas import UserPointsOut, CouponOut, UserRegisterIn, UserRegisterOut

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post("/register", response_model=UserRegisterOut)
async def register(body: UserRegisterIn, db: AsyncSession = Depends(get_session)):
    """정식 회원가입 — 전화번호를 포인트 적립용으로 입력한 것만으로는 회원가입이 되지 않으며,
    반드시 이 엔드포인트를 거쳐야 is_guest=False(정식 회원)로 전환된다."""
    phone = re.sub(r"\D", "", body.phone)
    if len(phone) != 11:
        raise HTTPException(status_code=400, detail="휴대폰 번호 11자리를 정확히 입력해 주세요")

    user, already_member = await register_user(db, phone, body.name)
    await db.commit()
    return UserRegisterOut(
        user_id=user.id,
        phone_number=user.phone_number,
        name=user.name,
        current_points=user.current_points,
        already_member=already_member,
    )

@router.get("/points/{phone}", response_model=UserPointsOut)
async def get_user_points(phone: str, db: AsyncSession = Depends(get_session)):
    user = await get_user_by_phone(db, phone)
    if user is None:
        raise HTTPException(status_code=404, detail="등록된 회원이 아닙니다")
    if await expire_old_points(db, user):
        await db.commit()
    membership = await get_membership(db, user.id)
    return UserPointsOut(
        user_id=user.id,
        phone_number=user.phone_number,
        name=user.name,
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