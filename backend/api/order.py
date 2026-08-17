from datetime import datetime, date as _date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.models import Order, OrderItem
from schemas.order_schemas import OrderIn, OrderOut, OrderItemOut
from schemas.coupon_schemas import DiscountOut
from dao import user_dao, order_dao, cart_dao, discount_dao

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _to_order_item_out(item: OrderItem) -> OrderItemOut:
    return OrderItemOut(
        menu_item_id=item.menu_item_id,
        name_ko=item.menu_item.name_ko if item.menu_item else "",
        quantity=item.quantity,
        unit_price=item.unit_price,
        total_price=item.total_price,
        selected_options=item.selected_options or [],
        special_note=item.special_note,
    )


@router.get("/active-discounts", response_model=list[DiscountOut])
async def get_active_discounts_public(db: AsyncSession = Depends(get_session)):
    """현재 활성화된 할인 목록 (인증 불필요, 키오스크 화면용)."""
    return [d for d in await discount_dao.get_active_discounts(db) if d.applicable_tier == "ALL"]


@router.get("/validate-coupon")
async def validate_coupon(
    code: str,
    subtotal: Decimal,
    phone: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    """쿠폰 인식 직후 실제 결제 가능 여부를 검증한다."""
    coupon = await user_dao.get_coupon_by_code(db, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="유효하지 않은 쿠폰입니다")
    today = _date.today()
    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="비활성화되었거나 사용량이 소진된 쿠폰입니다")
    if coupon.max_usage_count > 0 and coupon.used_count >= coupon.max_usage_count:
        coupon.is_active = False
        await db.commit()
        raise HTTPException(status_code=400, detail="사용 횟수가 소진된 쿠폰입니다")
    if coupon.valid_from and today < coupon.valid_from:
        raise HTTPException(status_code=400, detail="아직 사용할 수 없는 쿠폰입니다")
    if coupon.valid_until and today > coupon.valid_until:
        raise HTTPException(status_code=400, detail="유효기간이 만료된 쿠폰입니다")
    if not phone:
        raise HTTPException(status_code=400, detail="쿠폰 사용을 위해 회원 전화번호를 먼저 확인해 주세요")
    user = await user_dao.get_user_by_phone(db, phone)
    if not user:
        raise HTTPException(status_code=400, detail="쿠폰을 보유한 회원을 찾을 수 없습니다")
    user_coupon = await user_dao.get_user_coupon_by_code(db, user.id, code)
    if not user_coupon:
        raise HTTPException(status_code=400, detail="보유하지 않았거나 이미 사용한 쿠폰입니다")
    if subtotal < coupon.min_order_amount:
        raise HTTPException(status_code=400, detail=f"쿠폰 최소 주문금액 {coupon.min_order_amount}원 미달입니다")
    if coupon.discount_type == "CASH":
        discount_amount = coupon.discount_value
    else:
        discount_amount = subtotal * coupon.discount_value / Decimal("100")
    discount_amount = min(discount_amount, subtotal)
    return {
        "valid": True,
        "discount_amount": discount_amount,
        "final_amount": max(Decimal("0"), subtotal - discount_amount),
    }


@router.get("/preview-discount")
async def preview_discount(session_id: str, db: AsyncSession = Depends(get_session)):
    """장바구니 기준으로 적용 가능한 할인 금액을 미리 계산해 반환한다 (주문 생성 없음)."""
    cart = await cart_dao.get_cart_with_items(db, session_id)
    if not cart or not cart.items:
        return {"discount_amount": 0.0, "final_amount": 0.0, "applicable": []}

    subtotal = sum(item.unit_price * item.quantity for item in cart.items)
    discount_amount = Decimal("0")
    applicable = []

    active_discounts = await discount_dao.get_active_discounts(db)
    today = _date.today()
    for disc in active_discounts:
        if disc.applicable_tier != "ALL":
            continue
        if disc.valid_from and today < disc.valid_from:
            continue
        if disc.valid_until and today > disc.valid_until:
            continue

        if disc.target_type == "ALL":
            base = subtotal
        elif disc.target_type == "CATEGORY":
            base = sum(
                item.unit_price * item.quantity
                for item in cart.items
                if item.menu_item and item.menu_item.category_id == disc.category_id
            )
        elif disc.target_type == "MENU":
            base = sum(
                item.unit_price * item.quantity
                for item in cart.items
                if item.menu_item_id == disc.menu_item_id
            )
        else:
            continue

        if base <= 0:
            continue

        if disc.discount_type == "PERCENT":
            d = base * disc.discount_value / Decimal("100")
        else:
            d = min(Decimal(str(disc.discount_value)), base)

        discount_amount += d
        applicable.append({"name": disc.name_ko, "amount": float(d)})

    discount_amount = min(discount_amount, subtotal)
    return {
        "discount_amount": float(discount_amount),
        "final_amount": float(subtotal - discount_amount),
        "applicable": applicable,
    }


@router.post("", response_model=OrderOut)
async def create_order(body: OrderIn, db: AsyncSession = Depends(get_session)):
    # 1. 장바구니 조회 및 검증
    cart = await cart_dao.get_cart_with_items(db, body.session_id)
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="장바구니가 비어있거나 존재하지 않습니다.")

    # 2. Subtotal 계산
    subtotal = sum(item.unit_price * item.quantity for item in cart.items)
    discount_amount = Decimal("0")
    user_coupon_id = None
    user = None

    # 3. 회원 조회 (전화번호 제공 시)
    if body.phone:
        user = await user_dao.get_user_by_phone(db, body.phone)
        if user is None:
            user = await user_dao.create_guest_user(db, body.phone)
        else:
            await user_dao.expire_old_points(db, user)

    # 4. 쿠폰 적용
    if body.coupon_code:
        if not user:
            raise HTTPException(status_code=400, detail="쿠폰은 회원만 사용할 수 있습니다.")
        user_coupon = await user_dao.get_user_coupon_by_code(db, user.id, body.coupon_code)
        if not user_coupon:
            raise HTTPException(status_code=400, detail="유효하지 않거나 이미 사용된 쿠폰입니다.")
        coupon = user_coupon.coupon
        if not coupon.is_active:
            raise HTTPException(status_code=400, detail="비활성화된 쿠폰입니다.")
        today = _date.today()
        if coupon.max_usage_count > 0 and coupon.used_count >= coupon.max_usage_count:
            coupon.is_active = False
            await db.commit()
            raise HTTPException(status_code=400, detail="사용 횟수가 소진된 쿠폰입니다.")
        if coupon.valid_from and today < coupon.valid_from:
            raise HTTPException(status_code=400, detail="아직 사용할 수 없는 쿠폰입니다.")
        if coupon.valid_until and today > coupon.valid_until:
            raise HTTPException(status_code=400, detail="유효기간이 만료된 쿠폰입니다.")
        if subtotal < coupon.min_order_amount:
            raise HTTPException(status_code=400, detail=f"최소 주문 금액({coupon.min_order_amount}원)을 충족하지 못했습니다.")
        if coupon.discount_type == "PERCENT":
            discount_amount = subtotal * (coupon.discount_value / Decimal("100"))
        else:
            discount_amount = coupon.discount_value
        user_coupon_id = user_coupon.id

    # 4.5. Discount 테이블 할인 적용 (ALL / CATEGORY / MENU, applicable_tier=ALL만)
    active_discounts = await discount_dao.get_active_discounts(db)
    today = _date.today()
    for disc in active_discounts:
        if disc.applicable_tier != "ALL":
            continue
        if disc.valid_from and today < disc.valid_from:
            continue
        if disc.valid_until and today > disc.valid_until:
            continue

        if disc.target_type == "ALL":
            base = subtotal
        elif disc.target_type == "CATEGORY":
            base = sum(
                item.unit_price * item.quantity
                for item in cart.items
                if item.menu_item and item.menu_item.category_id == disc.category_id
            )
        elif disc.target_type == "MENU":
            base = sum(
                item.unit_price * item.quantity
                for item in cart.items
                if item.menu_item_id == disc.menu_item_id
            )
        else:
            continue

        if base <= 0:
            continue

        if disc.discount_type == "PERCENT":
            discount_amount += base * disc.discount_value / Decimal("100")
        else:
            discount_amount += min(Decimal(str(disc.discount_value)), base)

    discount_amount = min(discount_amount, subtotal)

    # 5. 포인트 사용 및 적립 계산 (결제금액의 5% 적립)
    points_to_use = body.points_to_use or 0
    if points_to_use > 0:
        if not user:
            raise HTTPException(status_code=400, detail="포인트 사용은 회원만 가능합니다.")
        if user.current_points < points_to_use:
            raise HTTPException(status_code=400, detail="보유 포인트가 부족합니다.")

    final_amount = max(Decimal("0"), subtotal - discount_amount - Decimal(points_to_use))
    points_earned = int(final_amount * Decimal("0.05"))

    # 6. 주문번호 생성 (당일 순번)
    count_result = await db.execute(sa_select(func.count(Order.id)))
    order_num = (count_result.scalar() or 0) + 1

    order = Order(
        user_id=user.id if user else None,
        cart_id=cart.id,
        order_number=str(order_num),
        order_type=body.order_type,
        status="RECEIVED",
        user_coupon_id=user_coupon_id,
        subtotal=subtotal,
        discount_amount=discount_amount,
        final_amount=final_amount,
        points_used=points_to_use,
        points_earned=points_earned,
    )
    db.add(order)
    await db.flush()

    # 7. 주문 항목 복사
    order_items = []
    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=cart_item.menu_item_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.unit_price * cart_item.quantity,
            selected_options=cart_item.selected_options,
            special_note=cart_item.special_note,
        )
        order_item.menu_item = cart_item.menu_item
        db.add(order_item)
        order_items.append(order_item)

    # 8. 쿠폰 사용 처리 및 포인트 FIFO 차감/적립
    if user_coupon_id:
        await user_dao.mark_coupon_used(db, user_coupon_id)

    if user:
        if points_to_use:
            await user_dao.consume_points_fifo(db, user.id, points_to_use)
        if points_earned:
            await user_dao.create_point_earn_log(db, user.id, order.id, points_earned)
        user.current_points = max(0, user.current_points - points_to_use) + points_earned

    # 9. 장바구니 완료 처리
    cart.status = "COMPLETED"
    await db.commit()
    await db.refresh(order)

    items_out = [_to_order_item_out(item) for item in order_items]

    return OrderOut(
        order_id=order.id,
        order_number=order.order_number,
        order_type=order.order_type,
        status=order.status,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        final_amount=order.final_amount,
        points_used=order.points_used,
        points_earned=order.points_earned,
        items=items_out,
    )


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: str, db: AsyncSession = Depends(get_session)):
    order = await order_dao.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")

    items_out = [_to_order_item_out(item) for item in order.items]

    return OrderOut(
        order_id=order.id,
        order_number=order.order_number,
        order_type=order.order_type,
        status=order.status,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        final_amount=order.final_amount,
        points_used=order.points_used,
        points_earned=order.points_earned,
        items=items_out,
    )
