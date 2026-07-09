from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from core.db import get_db
from dao.cart_dao import get_cart_with_items
from dao.order_dao import create_order_from_cart, create_order_items_from_cart_items, get_order_by_id
from schemas.order_schemas import OrderIn, OrderOut

router = APIRouter(prefix="/api/orders", tags=["order"])

@router.post("", response_model=OrderOut)
async def create_order(body: OrderIn, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_with_items(db, body.session_id)
    if cart is None or not cart.items:
        raise HTTPException(status_code=400, detail="장바구니가 비어있습니다")

    subtotal = sum(ci.unit_price * ci.quantity for ci in cart.items)
    discount_amount = Decimal("0")
    # TODO: 쿠폰 적용 로직 추가 (coupon_code 검증 → discount 계산)
    final_amount = subtotal - discount_amount - (body.points_to_use or 0)
    points_earned = int(final_amount * Decimal("0.05"))  # 결제금액 5% 적립

    order = await create_order_from_cart(
        db, cart.id, body.order_type, subtotal,
        discount_amount, final_amount, body.points_to_use, points_earned
    )
    await create_order_items_from_cart_items(db, order.id, cart.items)

    # 장바구니 상태 COMPLETED로 변경
    cart.status = "COMPLETED"
    await db.commit()

    order_with_items = await get_order_by_id(db, order.id)
    return OrderOut(
        order_id=order.id,
        order_number=order.order_number,
        order_type=order.order_type,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        final_amount=order.final_amount,
        points_used=order.points_used,
        points_earned=order.points_earned,
        items=[],  # 필요 시 items 직렬화 추가
    )

@router.get("/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
    return {"order_id": order.id, "order_number": order.order_number, "status": "completed"}