from pydantic import BaseModel
from typing import List, Optional


class MenuOptionSchema(BaseModel):
    id: str
    name: str
    price: int
    option_group: Optional[str] = None

    class Config:
        from_attributes = True


class MenuItemSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: int
    image_url: Optional[str] = None
    is_available: bool = True
    options: List[MenuOptionSchema] = []

    class Config:
        from_attributes = True


class CategorySchema(BaseModel):
    id: str
    name: str
    items: List[MenuItemSchema] = []

    class Config:
        from_attributes = True


class MenuResponse(BaseModel):
    categories: List[CategorySchema]
