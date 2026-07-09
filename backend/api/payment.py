from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_session
from dao.payment_dao import create_payment
from schemas.payment_schemas import PaymentIn, PaymentOut

router = APIRouter(prefix="/api/payments", tags=["payment"])

@router.post("", response_model=PaymentOut)
async def process_payment(body: PaymentIn, db: AsyncSession = Depends(get_session)):
    try:
        payment = await create_payment(
            db=db,
            order_id=body.order_id,
            method=body.method,
            amount=body.amount,
            pg_transaction_id=body.pg_transaction_id,
            pg_provider=body.pg_provider
        )
        await db.commit()
        return PaymentOut(
            payment_id=payment.id,
            order_id=payment.order_id,
            method=payment.method,
            amount=payment.amount,
            status=payment.status,
            paid_at=str(payment.paid_at) if payment.paid_at else None
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="결제 처리 중 오류가 발생했습니다.")