from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.dao import order_dao
from backend.schemas.order_schemas import OrderAdminOut, OrderItemOut

# 명세서 규칙: 상태 전이는 앞으로만 가능 (CANCELLED는 COMPLETED 제외하고 항상 허용)
_ORDER_STEPS = ["RECEIVED", "COOKING", "READY", "COMPLETED"]

def _is_valid_transition(current: str, new: str) -> bool:
    if new == "CANCELLED":
        return current != "COMPLETED"
    if current == "CANCELLED":
        return False
    if current not in _ORDER_STEPS or new not in _ORDER_STEPS:
        return False
    return _ORDER_STEPS.index(new) > _ORDER_STEPS.index(current)


router = APIRouter(prefix="/api/admin/orders", tags=["admin-orders"])


@router.get("", response_model=list[OrderAdminOut])
def get_admin_orders(
    status: str | None = None, 
    order_type: str | None = None, 
    db: Session = Depends(get_db)
):
    """관리자 주문 목록 조회"""
    orders = order_dao.list_orders(db, status=status, order_type=order_type)
    
    result = []
    for order in orders:
        # 결제 상태 확인 (가장 최근 결제)
        payment_status = order.payments[-1].status if order.payments else None
        
        items_out = [
            OrderItemOut(
                id=item.id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                total_price=float(item.total_price),
                selected_options=item.selected_options or [],
                special_note=item.special_note,
            )
            for item in order.items
        ]
        
        result.append(
            OrderAdminOut(
                id=order.id,
                order_number=order.order_number,
                order_type=order.order_type,
                status=order.status,
                table_number=order.table_number,
                subtotal=float(order.subtotal),
                discount_amount=float(order.discount_amount),
                final_amount=float(order.final_amount),
                points_used=order.points_used,
                points_earned=order.points_earned,
                items=items_out,
                created_at=order.created_at,
                payment_status=payment_status,
            )
        )
    return result


@router.patch("/{order_id}/status", response_model=OrderAdminOut)
def update_status(
    order_id: str, 
    status: str, 
    db: Session = Depends(get_db)
):
    """관리자 주문 상태 변경"""
    order = order_dao.list_orders(db) # 전체 중 해당 order 찾기
    target_order = next((o for o in order if o.id == order_id), None)
    
    if not target_order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
    
    # 상태 전이 검증 (역방향 금지)
    if not _is_valid_transition(target_order.status, status):
        raise HTTPException(
            status_code=400, 
            detail=f"'{target_order.status}'에서 '{status}'(으)로 상태를 변경할 수 없습니다."
        )
    
    updated_order = order_dao.update_order_status(db, order_id, status)
    db.commit()
    db.refresh(updated_order)
    
    payment_status = updated_order.payments[-1].status if updated_order.payments else None
    items_out = [
        OrderItemOut(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            unit_price=float(item.unit_price),
            total_price=float(item.total_price),
            selected_options=item.selected_options or [],
            special_note=item.special_note,
        )
        for item in updated_order.items
    ]
    
    return OrderAdminOut(
        id=updated_order.id,
        order_number=updated_order.order_number,
        order_type=updated_order.order_type,
        status=updated_order.status,
        table_number=updated_order.table_number,
        subtotal=float(updated_order.subtotal),
        discount_amount=float(updated_order.discount_amount),
        final_amount=float(updated_order.final_amount),
        points_used=updated_order.points_used,
        points_earned=updated_order.points_earned,
        items=items_out,
        created_at=updated_order.created_at,
        payment_status=payment_status,
    )
