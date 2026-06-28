from pydantic import BaseModel
from typing import List, Optional


class CartItemOptionSchema(BaseModel):
    option_id: str
    option_name: str
    price: int


class CartItemAddRequest(BaseModel):
    menu_item_id: str
    quantity: int = 1
    selected_options: List[str] = []


class CartItemSchema(BaseModel):
    id: str
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: int
    options: List[CartItemOptionSchema] = []
    subtotal: int

    class Config:
        from_attributes = True


class CartItemUpdateRequest(BaseModel):
    quantity: int


class CartResponse(BaseModel):
    session_id: str
    items: List[CartItemSchema] = []
    total_price: int = 0
