from pydantic import BaseModel


class UserCouponOut(BaseModel):
    user_coupon_id: str
    user_id: str
    coupon_id: str
    issued_at: str
