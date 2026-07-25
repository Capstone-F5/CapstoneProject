from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from decimal import Decimal
from core.models import Order, OrderItem, Cart

async def create_order_from_cart(
    db: AsyncSession,
    cart_id: str,
    order_type: str,
    subtotal: Decimal,
    discount_amount: Decimal,
    final_amount: Decimal,
    points_used: int,
    points_earned: int,
    user_id: str | None = None,
) -> Order:
    # 주문번호: 당일 순번 (1~999)
    count_result = await db.execute(select(func.count(Order.id)))
    order_num = (count_result.scalar() or 0) + 1

    order = Order(
        user_id=user_id,
        cart_id=cart_id,
        order_number=str(order_num),
        order_type=order_type,
        subtotal=subtotal,
        discount_amount=discount_amount,
        final_amount=final_amount,
        points_used=points_used,
        points_earned=points_earned,
    )
    db.add(order)
    await db.flush()
    return order

async def create_order_items_from_cart_items(
    db: AsyncSession, order_id: str, cart_items: list
) -> None:
    for ci in cart_items:
        total = ci.unit_price * ci.quantity
        db.add(OrderItem(
            order_id=order_id,
            menu_item_id=ci.menu_item_id,
            quantity=ci.quantity,
            unit_price=ci.unit_price,
            total_price=total,
            selected_options=ci.selected_options,
            special_note=ci.special_note,
        ))

async def get_order_by_id(db: AsyncSession, order_id: str) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    return result.scalar_one_or_none()


async def get_recent_orders_by_user(
    db: AsyncSession, user_id: str, limit: int = 5
) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.menu_item),
            selectinload(Order.payments),
        )
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


from sqlalchemy.orm import Session
from backend.core.models import Order

def list_orders(db: Session, status: str | None = None, order_type: str | None = None):
    """관리자용 주문 목록 조회 (미완료 주문 우선 정렬)"""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    if order_type:
        query = query.filter(Order.order_type == order_type)
    
    # 최신순 정렬
    return query.order_by(Order.created_at.desc()).all()


def update_order_status(db: Session, order_id: str, new_status: str) -> Order | None:
    """주문 상태 변경 (DAO 규칙: flush만 호출)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.status = new_status
        db.flush()
    return order