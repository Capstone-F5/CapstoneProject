"""관리자 화면(결제 내역·주문 내역·통계) 확인용 더미 주문/결제 데이터를 넣는다.

사용법 (backend 폴더에서):
    python tools/seed_dummy_payments.py            # 최근 14일, 약 70건 추가 (이미 더미가 있으면 중단)
    python tools/seed_dummy_payments.py --reset    # 기존 더미를 지우고 다시 생성
    python tools/seed_dummy_payments.py --clear    # 더미만 삭제
    python tools/seed_dummy_payments.py --days 30 --count 150

더미 식별: 주문 admin_note가 '[DUMMY]'로 시작하고, 결제 pg_provider가 'DUMMY'(현금 제외 시 거래 ID도 'DUMMY-…').
실제 주문/결제는 건드리지 않는다. 메뉴는 DB에 이미 있는 항목을 사용한다.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import delete, func, select  # noqa: E402

from core.db import SessionLocal  # noqa: E402
from core.models import MenuItem, Order, OrderItem, Payment  # noqa: E402

TAG = "[DUMMY]"

# (결제 수단, 가중치, PG 제공자)
METHODS = [
    ("CARD", 50, "DUMMY"),
    ("SAMSUNG_PAY", 18, "DUMMY"),
    ("QR_PAY", 17, "DUMMY"),
    ("CASH", 15, None),
]
FAIL_REASONS = ["카드 한도 초과", "카드 인식 실패", "사용자 취소", "승인 거부", "통신 오류"]
NOTES = [None, None, None, "소스 많이", "양파 빼주세요", "빨리 부탁드려요", "포장 꼼꼼히"]


def pick_method(rng: random.Random):
    total = sum(w for _, w, _ in METHODS)
    r = rng.uniform(0, total)
    acc = 0
    for m, w, prov in METHODS:
        acc += w
        if r <= acc:
            return m, prov
    return METHODS[0][0], METHODS[0][2]


def random_time(rng: random.Random, day: datetime) -> datetime:
    """점심(12~14시)·저녁(18~20시)에 몰리게 시각을 뽑는다."""
    hour = rng.choices(
        [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        weights=[2, 3, 5, 14, 12, 6, 4, 4, 6, 14, 12, 6, 2],
    )[0]
    return day.replace(hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59), microsecond=0)


async def clear_dummy(session) -> int:
    ids = (await session.execute(select(Order.id).where(Order.admin_note.like(f"{TAG}%")))).scalars().all()
    if not ids:
        return 0
    await session.execute(delete(Payment).where(Payment.order_id.in_(ids)))
    await session.execute(delete(OrderItem).where(OrderItem.order_id.in_(ids)))
    await session.execute(delete(Order).where(Order.id.in_(ids)))
    await session.commit()
    return len(ids)


async def seed(days: int, count: int, seed_value: int) -> None:
    rng = random.Random(seed_value)
    async with SessionLocal() as session:
        menus = (await session.execute(select(MenuItem).where(MenuItem.is_available.is_(True)))).scalars().all()
        if not menus:
            print("메뉴가 없습니다. 백엔드를 한 번 시작해 메뉴 시드를 먼저 만드세요.")
            return
        existing = (await session.execute(
            select(func.count()).select_from(Order).where(Order.admin_note.like(f"{TAG}%"))
        )).scalar_one()
        if existing:
            print(f"이미 더미 주문 {existing}건이 있습니다. --reset 으로 다시 만들거나 --clear 로 지우세요.")
            return

        used_numbers = set((await session.execute(select(Order.order_number))).scalars().all())
        seq_by_day: dict[str, int] = {}
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        made = {"orders": 0, "SUCCESS": 0, "REFUNDED": 0, "FAILED": 0, "PENDING": 0}

        for _ in range(count):
            day = today - timedelta(days=rng.randint(0, days - 1))
            created = random_time(rng, day)
            if created > datetime.now():          # 오늘의 미래 시각은 피한다
                created = datetime.now() - timedelta(minutes=rng.randint(1, 90))

            key = created.strftime("%Y%m%d")
            seq = seq_by_day.get(key, 500)        # 실제 주문 번호(001~)와 겹치지 않게 500부터
            while f"{key}{seq:03d}" in used_numbers:
                seq += 1
            seq_by_day[key] = seq + 1
            order_number = f"{key}{seq:03d}"
            used_numbers.add(order_number)

            lines = []
            for menu in rng.sample(menus, k=min(len(menus), rng.choice([1, 1, 2, 2, 3, 4]))):
                qty = rng.choice([1, 1, 1, 2, 2, 3])
                unit = Decimal(menu.base_price)
                lines.append((menu, qty, unit, unit * qty))
            subtotal = sum(l[3] for l in lines)
            discount = (subtotal * Decimal("0.1")).quantize(Decimal("1")) if rng.random() < 0.15 else Decimal(0)
            final = subtotal - discount

            # 결제 결과 분포: 성공 84%, 환불 7%, 실패 6%, 대기 3%
            outcome = rng.choices(["SUCCESS", "REFUNDED", "FAILED", "PENDING"], weights=[84, 7, 6, 3])[0]
            if (datetime.now() - created) > timedelta(hours=1) and outcome == "PENDING":
                outcome = "SUCCESS"               # 오래된 결제가 대기 상태로 남는 건 부자연스럽다
            order_status = {
                "SUCCESS": "COMPLETED", "REFUNDED": "CANCELLED",
                "FAILED": "CANCELLED", "PENDING": "RECEIVED",
            }[outcome]

            order = Order(
                id=str(uuid.uuid4()),
                order_number=order_number,
                order_type=rng.choices(["EAT_IN", "TAKE_OUT"], weights=[60, 40])[0],
                status=order_status,
                subtotal=subtotal, discount_amount=discount, final_amount=final,
                points_earned=int(final * Decimal("0.01")) if outcome == "SUCCESS" and rng.random() < 0.3 else 0,
                admin_note=f"{TAG} 테스트용 데이터",
                created_at=created,
            )
            session.add(order)
            for menu, qty, unit, total in lines:
                session.add(OrderItem(
                    id=str(uuid.uuid4()), order_id=order.id, menu_item_id=menu.id,
                    quantity=qty, unit_price=unit, total_price=total,
                    selected_options=[], special_note=rng.choice(NOTES),
                ))

            method, provider = pick_method(rng)
            paid_at = created + timedelta(seconds=rng.randint(5, 40))
            payment = Payment(
                id=str(uuid.uuid4()), order_id=order.id, method=method, amount=final,
                pg_provider=provider,
                pg_transaction_id=f"DUMMY-{uuid.uuid4().hex[:16]}" if provider else None,
                status=outcome, created_at=created,
            )
            if outcome in ("SUCCESS", "REFUNDED"):
                payment.paid_at = paid_at
            if outcome == "REFUNDED":
                payment.refunded_at = paid_at + timedelta(minutes=rng.randint(3, 120))
            if outcome == "FAILED":
                payment.failure_reason = rng.choice(FAIL_REASONS)
            session.add(payment)
            made["orders"] += 1
            made[outcome] += 1

        await session.commit()
        print(f"더미 데이터 생성 완료: 주문/결제 {made['orders']}건 "
              f"(성공 {made['SUCCESS']}, 환불 {made['REFUNDED']}, 실패 {made['FAILED']}, 대기 {made['PENDING']})")


async def main() -> None:
    parser = argparse.ArgumentParser(description="더미 주문/결제 데이터 생성")
    parser.add_argument("--days", type=int, default=14, help="최근 N일에 분산 (기본 14)")
    parser.add_argument("--count", type=int, default=70, help="생성할 주문/결제 건수 (기본 70)")
    parser.add_argument("--seed", type=int, default=20260930, help="난수 시드(같은 값이면 같은 데이터)")
    parser.add_argument("--reset", action="store_true", help="기존 더미를 지우고 다시 생성")
    parser.add_argument("--clear", action="store_true", help="더미만 삭제하고 종료")
    args = parser.parse_args()

    if args.reset or args.clear:
        async with SessionLocal() as session:
            removed = await clear_dummy(session)
        print(f"기존 더미 {removed}건 삭제")
        if args.clear:
            return
    await seed(args.days, args.count, args.seed)


if __name__ == "__main__":
    asyncio.run(main())
