from pydantic import BaseModel
from decimal import Decimal

class PaymentIn(BaseModel):
    order_id: str
    method: str            # CARD | SAMSUNG_PAY | QR_PAY | CASH
    amount: Decimal
    pg_transaction_id: str | None = None
    pg_provider: str | None = None

class PaymentOut(BaseModel):
    payment_id: str
    order_id: str
    method: str
    amount: Decimal
    status: str
    paid_at: str | None