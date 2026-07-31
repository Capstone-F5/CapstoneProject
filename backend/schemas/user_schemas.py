from pydantic import BaseModel

class UserPointsOut(BaseModel):
    user_id: str
    phone_number: str
    name: str | None = None
    current_points: int
    tier: str | None  # BASIC | SILVER | GOLD

class UserRegisterIn(BaseModel):
    phone: str
    name: str | None = None

class UserRegisterOut(BaseModel):
    user_id: str
    phone_number: str
    name: str | None
    current_points: int
    already_member: bool  # 가입 시도 전에 이미 정식 회원이었는지 여부

class CouponOut(BaseModel):
    user_coupon_id: str
    coupon_code: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    is_used: bool
    valid_until: str | None