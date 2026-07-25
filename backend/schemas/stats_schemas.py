from decimal import Decimal
from pydantic import BaseModel


class StatsSummaryOut(BaseModel):
    today_sales: float
    order_count: int
    avg_order_value: float


class SalesPointOut(BaseModel):
    date: str  # YYYY-MM-DD
    sales: float
    order_count: int


class SalesSeriesOut(BaseModel):
    range: str
    data: list[SalesPointOut]


class PopularItemOut(BaseModel):
    menu_item_id: str
    name_ko: str
    quantity_sold: int
    revenue: float
    