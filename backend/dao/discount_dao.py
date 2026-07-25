from sqlalchemy.orm import Session
from backend.core.models import Discount
from backend.schemas.coupon_schemas import DiscountIn


def list_discounts(db: Session):
    return db.query(Discount).all()


def create_discount(db: Session, data: DiscountIn) -> Discount:
    discount = Discount(**data.model_dump())
    db.add(discount)
    db.flush()
    return discount
