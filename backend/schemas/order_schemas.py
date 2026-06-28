from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    completed = "completed"
    cancelled = "cancelled"


class OrderItemSchema(BaseModel):
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: int
    subtotal: int

    class Config:
        from_attributes = True


class OrderCreateRequest(BaseModel):
    session_id: str
    user_phone: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    session_id: str
    status: OrderStatus
    items: List[OrderItemSchema] = []
    total_price: int
    created_at: str

    class Config:
        from_attributes = True
