from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.dao import stats_dao
from backend.schemas.stats_schemas import (
    StatsSummaryOut,
    SalesSeriesOut,
    SalesPointOut,
    PopularItemOut,
)

router = APIRouter(prefix="/api/admin/stats", tags=["admin-stats"])


@router.get("/summary", response_model=StatsSummaryOut)
def get_summary(db: Session = Depends(get_db)):
    """오늘의 매출 요약 통계"""
    data = stats_dao.get_today_summary(db)
    return StatsSummaryOut(**data)


@router.get("/sales", response_model=SalesSeriesOut)
def get_sales(range: str = "7d", db: Session = Depends(get_db)):
    """일자별 매출 추이 (기본 7일)"""
    days = 30 if range == "30d" else 7
    series = stats_dao.get_sales_series(db, days=days)
    return SalesSeriesOut(
        range=range,
        data=[SalesPointOut(**point) for point in series]
    )


@router.get("/popular-items", response_model=list[PopularItemOut])
def get_popular_items(range: str = "7d", db: Session = Depends(get_db)):
    """인기 메뉴 랭킹"""
    days = 30 if range == "30d" else 7
    items = stats_dao.get_popular_items(db, days=days)
    return [PopularItemOut(**item) for item in items]