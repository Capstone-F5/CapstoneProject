from pydantic import BaseModel
from typing import Optional
from enum import Enum


class PaymentMethod(str, Enum):
    card = "card"
    cash = "cash"
    points = "points"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PaymentCreateRequest(BaseModel):
    order_id: str
    method: PaymentMethod
    amount: int
    use_points: int = 0


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    method: PaymentMethod
    status: PaymentStatus
    amount: int
    created_at: str

    class Config:
        from_attributes = True
