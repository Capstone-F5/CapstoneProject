from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class CouponIn(BaseModel):
    code: str
    discount_type: str  # CASH | PERCENT
    discount_value: Decimal
    min_order_amount: Decimal = Decimal("0")
    max_usage_count: int = 0  # 0 = 무제한
    valid_from: date | None = None
    valid_until: date | None = None


class CouponOut(CouponIn):
    id: str
    used_count: int
    is_active: bool

    class Config:
        from_attributes = True


class UserCouponOut(BaseModel):
    user_coupon_id: str
    user_id: str
    coupon_id: str
    issued_at: datetime

    class Config:
        from_attributes = True


class DiscountIn(BaseModel):
    target_type: str  # MENU | CATEGORY | ALL
    menu_item_id: str | None = None
    category_id: str | None = None
    discount_type: str  # CASH | PERCENT
    discount_value: Decimal
    name_ko: str
    name_en: str
    valid_from: date | None = None
    valid_until: date | None = None
    applicable_tier: str = "ALL"


class DiscountOut(DiscountIn):
    id: str
    is_active: bool

    class Config:
        from_attributes = True