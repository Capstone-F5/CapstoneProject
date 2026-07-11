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