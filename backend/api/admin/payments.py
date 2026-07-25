from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.dao import payment_dao, order_dao, user_dao
from backend.schemas.payment_schemas import PaymentAdminOut, RefundReq

router = APIRouter(prefix="/api/admin/payments", tags=["admin-payments"])


@router.get("", response_model=list[PaymentAdminOut])
def get_payments(status: str | None = None, db: Session = Depends(get_db)):
    payments = payment_dao.list_payments(db, status=status)
    return [
        PaymentAdminOut(
            payment_id=p.id,
            order_id=p.order_id,
            order_number=p.order.order_number if p.order else "",
            method=p.method,
            amount=float(p.amount),
            status=p.status,
            pg_transaction_id=p.pg_transaction_id,
            failure_reason=p.failure_reason,
            paid_at=p.paid_at,
            refunded_at=p.refunded_at,
        )
        for p in payments
    ]


@router.post("/{id}/refund", response_model=PaymentAdminOut)
def refund_payment(id: str, body: RefundReq, db: Session = Depends(get_db)):
    """결제 환불 API:
    1. 포인트 원상복구 (적립 회수, 사용분 반환)
    2. 사용된 쿠폰 복구 (is_used=False)
    3. 결제 상태 -> REFUNDED, 주문 상태 -> CANCELLED
    """
    payment = payment_dao.get_payment_by_id(db, id)
    if not payment:
        raise HTTPException(status_code=404, detail="결제 내역을 찾을 수 없습니다.")
    if payment.status == "REFUNDED":
        raise HTTPException(status_code=409, detail="이미 환불된 결제입니다.")

    order = payment.order
    if not order:
        raise HTTPException(status_code=404, detail="연결된 주문 내역을 찾을 수 없습니다.")

    # 1. 포인트 원상복구: (적립분 - 사용분)의 반대값으로 역산
    if order.user_id:
        net_point_change = order.points_earned - order.points_used
        user_dao.adjust_points(db, order.user_id, -net_point_change)

    # 2. 쿠폰 원상복구
    if order.user_coupon_id:
        user_dao.restore_coupon(db, order.user_coupon_id)

    # 3. 결제 상태 REFUNDED 및 주문 상태 CANCELLED로 변경
    updated_payment = payment_dao.mark_refunded(db, id, body.reason)
    order_dao.update_order_status(db, order.id, "CANCELLED")

    db.commit()
    db.refresh(updated_payment)

    return PaymentAdminOut(
        payment_id=updated_payment.id,
        order_id=updated_payment.order_id,
        order_number=order.order_number,
        method=updated_payment.method,
        amount=float(updated_payment.amount),
        status=updated_payment.status,
        pg_transaction_id=updated_payment.pg_transaction_id,
        failure_reason=updated_payment.failure_reason,
        paid_at=updated_payment.paid_at,
        refunded_at=updated_payment.refunded_at,
    )