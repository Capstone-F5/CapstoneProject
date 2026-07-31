from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from core.db import get_session
from dao.cart_dao import get_cart_with_items
from dao.order_dao import create_order_from_cart, create_order_items_from_cart_items, get_order_by_id
from dao import user_dao
from schemas.order_schemas import OrderIn, OrderOut, OrderItemOut

router = APIRouter(prefix="/api/orders", tags=["order"])


def _compute_discount(coupon, subtotal: Decimal) -> Decimal:
    """쿠폰 할인액 계산. 최소 주문금액 미달이면 400을 던진다."""
    if subtotal < coupon.min_order_amount:
        raise HTTPException(
            status_code=400,
            detail=f"쿠폰 최소 주문금액 {coupon.min_order_amount}원 미달입니다",
        )
    if coupon.discount_type == "CASH":
        discount_amount = coupon.discount_value
    else:  # PERCENT
        discount_amount = subtotal * coupon.discount_value / Decimal("100")
    return min(discount_amount, subtotal)


@router.get("/validate-coupon")
async def validate_coupon(code: str, subtotal: Decimal, db: AsyncSession = Depends(get_session)):
    """결제 진행 전 쿠폰 코드를 미리 검증해 할인 금액을 보여주기 위한 엔드포인트."""
    coupon = await user_dao.get_coupon_by_code(db, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="유효하지 않은 쿠폰입니다")
    discount_amount = _compute_discount(coupon, subtotal)
    return {
        "valid": True,
        "discount_amount": discount_amount,
        "final_amount": max(Decimal("0"), subtotal - discount_amount),
    }


@router.post("", response_model=OrderOut)
async def create_order(body: OrderIn, db: AsyncSession = Depends(get_session)):
    cart = await get_cart_with_items(db, body.session_id)
    if cart is None or not cart.items:
        raise HTTPException(status_code=400, detail="장바구니가 비어있습니다")

    subtotal = sum(ci.unit_price * ci.quantity for ci in cart.items)

    user = None
    if body.phone:
        user = await user_dao.get_user_by_phone(db, body.phone)
        if user is None:
            user = await user_dao.create_guest_user(db, body.phone)
        else:
            # 적립 후 30일 지난 포인트를 먼저 만료 처리해 최신 잔액 기준으로 계산한다
            await user_dao.expire_old_points(db, user)

    discount_amount = Decimal("0")
    user_coupon = None
    if body.coupon_code:
        coupon = await user_dao.get_coupon_by_code(db, body.coupon_code)
        if coupon is None:
            raise HTTPException(status_code=400, detail="유효하지 않은 쿠폰입니다")
        discount_amount = _compute_discount(coupon, subtotal)
        if user:
            user_coupon = await user_dao.get_user_coupon(db, user.id, coupon.id)

    points_to_use = body.points_to_use or 0
    final_amount = max(Decimal("0"), subtotal - discount_amount - points_to_use)
    points_earned = int(final_amount * Decimal("0.05"))  # 결제금액 5% 적립

    order = await create_order_from_cart(
        db, cart.id, body.order_type, subtotal,
        discount_amount, final_amount, points_to_use, points_earned,
        user_id=user.id if user else None,
    )
    await create_order_items_from_cart_items(db, order.id, cart.items)

    if user:
        user.current_points = max(0, user.current_points - points_to_use) + points_earned
        if points_to_use:
            await user_dao.consume_points_fifo(db, user.id, points_to_use)
        if points_earned:
            await user_dao.create_point_earn_log(db, user.id, order.id, points_earned)
    if user_coupon:
        user_coupon.is_used = True

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
        items=[
            OrderItemOut(
                menu_item_id=i.menu_item_id,
                name_ko=i.menu_item.name_ko if i.menu_item else "",
                quantity=i.quantity,
                unit_price=i.unit_price,
                total_price=i.total_price,
                selected_options=i.selected_options or [],
                special_note=i.special_note,
            )
            for i in order_with_items.items
        ],
    )

@router.get("/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_session)):
    order = await get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "created_at": str(order.created_at),
    }