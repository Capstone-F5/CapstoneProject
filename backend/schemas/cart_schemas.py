from pydantic import BaseModel
from decimal import Decimal

class SelectedOption(BaseModel):
    option_id: str
    name: str

class CartItemIn(BaseModel):
    menu_item_id: str
    quantity: int = 1
    selected_options: list[SelectedOption] = []
    special_note: str | None = None

class CartItemOut(BaseModel):
    cart_item_id: str
    menu_item_id: str
    name_ko: str
    quantity: int
    unit_price: Decimal
    selected_options: list[SelectedOption]
    special_note: str | None

class CartItemUpdateIn(BaseModel):
    quantity: int | None = None
    selected_options: list[SelectedOption] | None = None
    special_note: str | None = None

class CartOut(BaseModel):
    cart_id: str
    session_id: str
    items: list[CartItemOut]
    total: Decimal