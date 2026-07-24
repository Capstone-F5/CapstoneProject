from pydantic import BaseModel
from decimal import Decimal

class MenuOptionOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    additional_price: Decimal
    is_available: bool
    display_order: int
    option_group: str  # SET_UPGRADE | EXCLUDE | SET_SIDE | SET_DRINK

    model_config = {"from_attributes": True}

class AllergenOut(BaseModel):
    code: str
    name_ko: str
    name_en: str

    model_config = {"from_attributes": True}

class MenuItemOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    base_price: Decimal
    description: str
    image_url: str | None
    set_image_url: str | None
    is_available: bool
    is_popular: bool
    is_new: bool
    display_order: int
    options: list[MenuOptionOut] = []
    allergens: list[AllergenOut] = []

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


# --- 관리자용 요청 스키마 (Module B) ---------------------------------------
class CategoryIn(BaseModel):
    name_ko: str
    name_en: str
    display_order: int = 0
    is_visible: bool = True
    image_url: str | None = None


class CategoryPatchIn(BaseModel):
    name_ko: str | None = None
    name_en: str | None = None
    display_order: int | None = None
    is_visible: bool | None = None
    image_url: str | None = None


class MenuItemIn(BaseModel):
    category_id: str
    name_ko: str
    name_en: str
    base_price: Decimal
    description: str = ""
    image_url: str | None = None
    set_image_url: str | None = None
    is_available: bool = True
    is_popular: bool = False
    is_new: bool = False
    display_order: int = 0


class MenuItemPatchIn(BaseModel):
    category_id: str | None = None
    name_ko: str | None = None
    name_en: str | None = None
    base_price: Decimal | None = None
    description: str | None = None
    image_url: str | None = None
    set_image_url: str | None = None
    is_available: bool | None = None
    is_popular: bool | None = None
    is_new: bool | None = None
    display_order: int | None = None


class MenuOptionIn(BaseModel):
    name_ko: str
    name_en: str
    description: str = ""
    additional_price: Decimal = Decimal("0")
    is_available: bool = True
    display_order: int = 0


class MenuOptionPatchIn(BaseModel):
    name_ko: str | None = None
    name_en: str | None = None
    description: str | None = None
    additional_price: Decimal | None = None
    is_available: bool | None = None
    display_order: int | None = None