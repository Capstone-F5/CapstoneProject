from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import Order, OrderItem, MenuItem, Category, Payment


def _revenue_filter():
    """매출 집계 대상 주문 조건.

    주방 진행 상태(COMPLETED)가 아니라 결제 성공 여부를 기준으로 한다.
    키오스크는 결제가 끝나면 주문을 RECEIVED로 쌓고 직원이 COMPLETED까지 직접 넘기는데,
    COMPLETED로 좁히면 상태를 넘기기 전까지 매출이 0으로 보인다.
    IN 서브쿼리를 쓰는 이유는 Payment를 join하면 결제가 여러 건인 주문의 금액이 중복 합산되기 때문.
    """
    paid = select(Payment.order_id).where(Payment.status == "SUCCESS")
    return (Order.status != "CANCELLED", Order.id.in_(paid))


async def get_today_summary(db: AsyncSession) -> dict:
    """오늘 매출 합계, 주문 건수, 평균 객단가"""
    today = date.today()
    result = await db.execute(
        select(Order).where(
            *_revenue_filter(),
            func.date(Order.created_at) == today,
        )
    )
    orders = result.scalars().all()

    order_count = len(orders)
    today_sales = sum(float(o.final_amount) for o in orders)
    avg_order_value = (today_sales / order_count) if order_count > 0 else 0.0

    return {
        "today_sales": today_sales,
        "order_count": order_count,
        "avg_order_value": avg_order_value,
    }


async def get_sales_series(db: AsyncSession, days: int) -> list[dict]:
    """최근 N일간 일자별 매출 추이"""
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(Order).where(
            *_revenue_filter(),
            func.date(Order.created_at) >= start_date,
        )
    )
    orders = result.scalars().all()

    daily_map = {}
    for i in range(days + 1):
        d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_map[d_str] = {"sales": 0.0, "order_count": 0}

    for o in orders:
        d_str = o.created_at.strftime("%Y-%m-%d")
        if d_str in daily_map:
            daily_map[d_str]["sales"] += float(o.final_amount)
            daily_map[d_str]["order_count"] += 1

    return [
        {"date": d_str, "sales": data["sales"], "order_count": data["order_count"]}
        for d_str, data in sorted(daily_map.items())
    ]


async def get_popular_items(db: AsyncSession, days: int, limit: int = 5) -> list[dict]:
    """인기 메뉴 랭킹 (판매 수량 및 매출액 기준)"""
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            OrderItem.menu_item_id,
            MenuItem.name_ko,
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(OrderItem.total_price).label("revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .where(
            *_revenue_filter(),
            func.date(Order.created_at) >= start_date,
        )
        .group_by(OrderItem.menu_item_id, MenuItem.name_ko)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )

    return [
        {
            "menu_item_id": r.menu_item_id,
            "name_ko": r.name_ko,
            "quantity_sold": int(r.quantity_sold),
            "revenue": float(r.revenue),
        }
        for r in result.all()
    ]


async def get_category_sales(db: AsyncSession, days: int) -> list[dict]:
    """카테고리별 매출 비율"""
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            Category.id,
            Category.name_ko,
            func.sum(OrderItem.total_price).label("revenue"),
            func.sum(OrderItem.quantity).label("quantity_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Category, MenuItem.category_id == Category.id)
        .where(
            *_revenue_filter(),
            func.date(Order.created_at) >= start_date,
        )
        .group_by(Category.id, Category.name_ko)
        .order_by(func.sum(OrderItem.total_price).desc())
    )
    rows = result.all()
    total_revenue = sum(float(r.revenue) for r in rows) or 1.0
    return [
        {
            "category_id": r.id,
            "name_ko": r.name_ko,
            "revenue": float(r.revenue),
            "quantity_sold": int(r.quantity_sold),
            "ratio": round(float(r.revenue) / total_revenue * 100, 1),
        }
        for r in rows
    ]


async def get_payment_method_stats(db: AsyncSession, days: int) -> list[dict]:
    """결제수단별 건수 및 합계"""
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            Payment.method,
            func.count(Payment.id).label("count"),
            func.sum(Payment.amount).label("total_amount"),
        )
        .join(Order, Payment.order_id == Order.id)
        .where(
            Payment.status == "SUCCESS",
            Order.status != "CANCELLED",
            func.date(Order.created_at) >= start_date,
        )
        .group_by(Payment.method)
        .order_by(func.sum(Payment.amount).desc())
    )
    return [
        {
            "method": r.method,
            "count": int(r.count),
            "total_amount": float(r.total_amount),
        }
        for r in result.all()
    ]
