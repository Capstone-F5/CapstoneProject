from pydantic import BaseModel

from schemas.coupon_schemas import UserCouponOut
from schemas.order_schemas import OrderAdminOut


class UserAdminOut(BaseModel):
    id: str
    phone_number: str | None
    current_points: int
    tier: str | None
    is_guest: bool
    created_at: str


class UserDetailOut(UserAdminOut):
    recent_orders: list[OrderAdminOut]  # 최근 N건, Module E 스키마 재사용
    coupons: list[UserCouponOut]  # 보유 쿠폰, Module F 스키마 재사용


class PointsAdjustIn(BaseModel):
    delta: int
    reason: str


class TierUpdateIn(BaseModel):
    tier: str  # BASIC | SILVER | GOLD
