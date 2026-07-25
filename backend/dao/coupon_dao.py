from sqlalchemy.orm import Session
from backend.core.models import Coupon, UserCoupon, User
from backend.schemas.coupon_schemas import CouponIn


def list_coupons(db: Session):
    return db.query(Coupon).all()


def create_coupon(db: Session, data: CouponIn) -> Coupon:
    coupon = Coupon(**data.model_dump())
    db.add(coupon)
    db.flush()
    return coupon


def issue_coupon_to_user(db: Session, coupon_id: str, phone: str) -> UserCoupon:
    user = db.query(User).filter(User.phone_number == phone).first()
    if not user:
        raise ValueError("해당 전화번호의 회원을 찾을 수 없습니다.")

    user_coupon = UserCoupon(user_id=user.id, coupon_id=coupon_id)
    db.add(user_coupon)
    db.flush()
    return user_coupon
