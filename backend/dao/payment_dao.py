from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime
from core.models import Payment

async def create_payment(
    db: AsyncSession,
    order_id: str,
    method: str,
    amount: Decimal,
    pg_transaction_id: str | None = None,
    pg_provider: str | None = None,
) -> Payment:
    payment = Payment(
        order_id=order_id,
        method=method,
        amount=amount,
        pg_transaction_id=pg_transaction_id,
        pg_provider=pg_provider,
        status="SUCCESS",
        paid_at=datetime.utcnow(),
    )
    db.add(payment)
    await db.flush()
    return payment


from datetime import datetime
from sqlalchemy.orm import Session
from backend.core.models import Payment


def get_payment_by_id(db: Session, payment_id: str) -> Payment | None:
    return db.query(Payment).filter(Payment.id == payment_id).first()


def list_payments(db: Session, status: str | None = None) -> list[Payment]:
    query = db.query(Payment)
    if status:
        query = query.filter(Payment.status == status)
    return query.order_by(Payment.created_at.desc()).all()


def mark_refunded(db: Session, payment_id: str, reason: str) -> Payment | None:
    """결제 상태를 REFUNDED로 변경하고 사유 기록 (DAO 규칙: flush만 호출)"""
    payment = get_payment_by_id(db, payment_id)
    if payment:
        payment.status = "REFUNDED"
        payment.refunded_at = datetime.now()
        payment.failure_reason = reason
        db.flush()
    return payment