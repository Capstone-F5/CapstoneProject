from pydantic import BaseModel
from decimal import Decimal

class MenuOptionOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    additional_price: Decimal
    is_available: bool
    display_order: int

    model_config = {"from_attributes": True}

class MenuItemOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    base_price: Decimal
    description: str
    image_url: str | None
    is_available: bool
    is_popular: bool
    is_new: bool
    display_order: int
    options: list[MenuOptionOut] = []

    model_config = {"from_attributes": True}

class CategoryOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    display_order: int
    is_visible: bool
    image_url: str | None

    model_config = {"from_attributes": True}

# GET /api/menu 응답 최상위 구조
class MenuResponse(BaseModel):
    categories: list[CategoryOut]
    menu_items: dict[str, list[MenuItemOut]]  # category_slug → items