"""
LangChain 툴 정의 (Function Calling).

1. search_menu — RAG 기반 메뉴 검색 (할루시네이션 방지)
2. add_to_cart — CARTS / CART_ITEMS 연동, ★special_note 음성 비정형 요구사항 기록
3. approve_payment — ORDERS / PAYMENTS 트랜잭션 (장바구니 → 주문 → 결제)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.db import SessionLocal
from backend.core.models import (
    Cart,
    CartItem,
    MenuItem,
    Order,
    OrderItem,
    Payment,
)

from .rag import search_menu as rag_search
from .session_context import get_session_id


# ---------- 1. search_menu --------------------------------------------------

class SearchMenuArgs(BaseModel):
    query: str = Field(..., description="자연어 검색어 (ex: '치즈 많은 버거', '비건', '안 매운').")
    k: int = Field(5, description="반환할 결과 개수.", ge=1, le=10)


async def _search_menu(query: str, k: int = 5) -> dict[str, Any]:
    hits = await rag_search(query, k=k)
    return {
        "query": query,
        "results": [
            {
                "menu_item_id": h["id"],
                "name_ko": h["name_ko"],
                "name_en": h["name_en"],
                "base_price": h["base_price"],
                "description": h["description"],
                "is_available": h["is_available"],
                "options": h["options"],
            }
            for h in hits
        ],
    }


search_menu_tool = StructuredTool.from_function(
    coroutine=_search_menu,
    name="search_menu",
    description=(
        "메뉴 데이터베이스에서 RAG 로 메뉴를 검색한다. 사용자가 메뉴/가격/재료/추천을 물으면 "
        "반드시 이 툴로 사실을 확인한 뒤 답하라(할루시네이션 금지). "
        "반환된 menu_item_id, options[*].id 를 다른 툴 호출 시 그대로 사용해야 한다."
    ),
    args_schema=SearchMenuArgs,
)


# ---------- 2. add_to_cart --------------------------------------------------

class SelectedOption(BaseModel):
    option_id: str = Field(..., description="search_menu 결과의 options[*].id")
    name: str = Field(..., description="옵션 한국어 이름 (감사용)")


class AddToCartArgs(BaseModel):
    menu_item_id: str = Field(..., description="search_menu 로 얻은 메뉴 ID.")
    quantity: int = Field(1, ge=1, le=20)
    selected_options: list[SelectedOption] = Field(
        default_factory=list,
        description="채소 제외/세트 업그레이드 같은 정형 옵션. options[*].id 매핑.",
    )
    special_note: str | None = Field(
        default=None,
        description=(
            "★음성 비정형 요구사항. 메뉴 옵션으로 존재하지 않는 자연어 요청을 그대로 기록한다. "
            "예: '반으로 잘라주세요', '빵 부드럽게 데워주세요', '소스 따로', '덜 짜게'. "
            "이 값은 CART_ITEMS.special_note 에 TEXT 로 저장되어 주방으로 전송된다."
        ),
    )


async def _get_or_create_cart(session, session_id: str) -> Cart:
    result = await session.execute(
        select(Cart)
        .where(Cart.session_id == session_id, Cart.status == "ACTIVE")
        .order_by(Cart.created_at.desc())
    )
    cart = result.scalars().first()
    if cart:
        return cart
    cart = Cart(
        session_id=session_id,
        status="ACTIVE",
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    session.add(cart)
    await session.flush()
    return cart


async def _add_to_cart(
    menu_item_id: str,
    quantity: int = 1,
    selected_options: list[SelectedOption] | None = None,
    special_note: str | None = None,
) -> dict[str, Any]:
    session_id = get_session_id()
    selected_options = selected_options or []

    async with SessionLocal() as session:
        menu_item = await session.get(
            MenuItem, menu_item_id, options=[selectinload(MenuItem.options)]
        )
        if menu_item is None:
            return {"ok": False, "error": f"menu_item_id 가 존재하지 않습니다: {menu_item_id}"}
        if not menu_item.is_available:
            return {"ok": False, "error": f"{menu_item.name_ko} 는 현재 품절입니다."}

        # 단가 = base_price + sum(추가옵션 price)
        unit_price: Decimal = Decimal(menu_item.base_price)
        opt_map = {opt.id: opt for opt in menu_item.options}
        opt_payload: list[dict[str, Any]] = []
        for so in selected_options:
            opt = opt_map.get(so.option_id)
            if opt is None:
                return {
                    "ok": False,
                    "error": f"옵션 ID 가 이 메뉴에 속하지 않습니다: {so.option_id}",
                }
            unit_price += Decimal(opt.additional_price)
            opt_payload.append(
                {
                    "option_id": opt.id,
                    "name_ko": opt.name_ko,
                    "additional_price": float(opt.additional_price),
                }
            )

        cart = await _get_or_create_cart(session, session_id)

        # 중복 라인 가드: 같은 ACTIVE 카트에 (메뉴+옵션+special_note) 동일 라인 존재 시 거절.
        # 모델이 "결제 직전 add_to_cart 재호출" 같은 실수를 해도 서버에서 강제 차단.
        normalized_note = (special_note or "").strip() or None
        new_opt_ids = sorted(o["option_id"] for o in opt_payload)
        existing_q = await session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.menu_item_id == menu_item.id,
            )
        )
        for ex in existing_q.scalars().all():
            ex_opt_ids = sorted(
                (o or {}).get("option_id") for o in (ex.selected_options or [])
            )
            ex_note = (ex.special_note or "").strip() or None
            if ex_opt_ids == new_opt_ids and ex_note == normalized_note:
                return {
                    "ok": False,
                    "duplicate": True,
                    "error": (
                        f"이미 동일한 라인이 장바구니에 있습니다: {menu_item.name_ko} "
                        f"(수량 {ex.quantity}). 같은 메뉴를 다시 담지 마세요. "
                        f"결제를 진행하려면 approve_payment 를 호출하세요."
                    ),
                    "existing_cart_item_id": ex.id,
                    "existing_quantity": ex.quantity,
                }

        item = CartItem(
            cart_id=cart.id,
            menu_item_id=menu_item.id,
            quantity=quantity,
            unit_price=unit_price,
            selected_options=opt_payload,
            special_note=normalized_note,
        )
        session.add(item)
        await session.commit()

        return {
            "ok": True,
            "cart_id": cart.id,
            "cart_item_id": item.id,
            "menu_item_id": menu_item.id,
            "name_ko": menu_item.name_ko,
            "quantity": quantity,
            "unit_price": float(unit_price),
            "line_total": float(unit_price * quantity),
            "selected_options": opt_payload,
            "special_note": special_note,
        }


add_to_cart_tool = StructuredTool.from_function(
    coroutine=_add_to_cart,
    name="add_to_cart",
    description=(
        "선택한 메뉴를 사용자의 장바구니(CARTS)에 라인 아이템(CART_ITEMS)으로 추가한다. "
        "★ 사용자가 '반으로 잘라주세요', '빵 부드럽게', '소스 따로' 처럼 메뉴 옵션이 아닌 "
        "비정형 요구를 말하면 반드시 그 문장을 special_note 인자로 자연어 그대로 전달하라. "
        "옵션으로 존재하는 변경(채소 제외, 세트 업그레이드)은 selected_options 에 넣어라."
    ),
    args_schema=AddToCartArgs,
)


# ---------- 3. get_cart -----------------------------------------------------

class GetCartArgs(BaseModel):
    pass


async def _get_cart() -> dict[str, Any]:
    session_id = get_session_id()
    async with SessionLocal() as session:
        result = await session.execute(
            select(Cart)
            .where(Cart.session_id == session_id, Cart.status == "ACTIVE")
            .options(selectinload(Cart.items).selectinload(CartItem.menu_item))
            .order_by(Cart.created_at.desc())
        )
        cart = result.scalars().first()
        if cart is None or not cart.items:
            return {"is_empty": True, "items": [], "subtotal": 0.0}

        items: list[dict[str, Any]] = []
        subtotal = Decimal("0")
        for ci in cart.items:
            line_total = Decimal(ci.unit_price) * ci.quantity
            subtotal += line_total
            items.append(
                {
                    "cart_item_id": ci.id,
                    "menu_item_id": ci.menu_item_id,
                    "name_ko": ci.menu_item.name_ko,
                    "quantity": ci.quantity,
                    "unit_price": float(ci.unit_price),
                    "line_total": float(line_total),
                    "selected_options": ci.selected_options or [],
                    "special_note": ci.special_note,
                }
            )

        return {
            "is_empty": False,
            "cart_id": cart.id,
            "items": items,
            "subtotal": float(subtotal),
        }


get_cart_tool = StructuredTool.from_function(
    coroutine=_get_cart,
    name="get_cart",
    description=(
        "현재 세션의 ACTIVE 장바구니 내용(라인 아이템·수량·단가·special_note·총액)을 조회한다. "
        "사용자가 결제 의사를 표현하면 approve_payment 직전에 반드시 이 툴로 카트를 먼저 확인하고, "
        "비어있지 않으면 add_to_cart 호출 없이 곧바로 approve_payment 만 호출하라."
    ),
    args_schema=GetCartArgs,
)


# ---------- 4. approve_payment ---------------------------------------------

class ApprovePaymentArgs(BaseModel):
    method: str = Field("CARD", description="결제 방식: CARD / SAMSUNG_PAY / QR_PAY / CASH")
    order_type: str = Field("TAKE_OUT", description="EAT_IN 또는 TAKE_OUT")
    table_number: int | None = Field(None, description="EAT_IN 시 테이블 번호 (배리어프리)")


def _gen_order_number() -> str:
    return f"K{datetime.utcnow().strftime('%y%m%d%H%M%S')}{secrets.randbelow(100):02d}"


async def _approve_payment(
    method: str = "CARD",
    order_type: str = "TAKE_OUT",
    table_number: int | None = None,
) -> dict[str, Any]:
    session_id = get_session_id()
    method = method.upper()
    order_type = order_type.upper()

    async with SessionLocal() as session:
        result = await session.execute(
            select(Cart)
            .where(Cart.session_id == session_id, Cart.status == "ACTIVE")
            .options(selectinload(Cart.items).selectinload(CartItem.menu_item))
            .order_by(Cart.created_at.desc())
        )
        cart = result.scalars().first()
        if cart is None or not cart.items:
            return {"ok": False, "error": "장바구니가 비어 있습니다. 메뉴를 먼저 담아주세요."}

        subtotal = Decimal("0")
        for ci in cart.items:
            subtotal += Decimal(ci.unit_price) * ci.quantity

        discount_amount = Decimal("0")  # 쿠폰/프로모션은 향후 확장
        final_amount = subtotal - discount_amount

        order = Order(
            cart_id=cart.id,
            order_number=_gen_order_number(),
            order_type=order_type if order_type in ("EAT_IN", "TAKE_OUT") else "TAKE_OUT",
            table_number=table_number,
            subtotal=subtotal,
            discount_amount=discount_amount,
            final_amount=final_amount,
        )
        session.add(order)
        await session.flush()

        for ci in cart.items:
            session.add(
                OrderItem(
                    order_id=order.id,
                    menu_item_id=ci.menu_item_id,
                    quantity=ci.quantity,
                    unit_price=ci.unit_price,
                    total_price=Decimal(ci.unit_price) * ci.quantity,
                    selected_options=ci.selected_options,
                    special_note=ci.special_note,  # 주방으로 그대로 전달
                )
            )

        # 가상 PG: 항상 승인 (실 PG 연동 전)
        payment = Payment(
            order_id=order.id,
            method=method if method in ("CARD", "SAMSUNG_PAY", "QR_PAY", "CASH") else "CARD",
            amount=final_amount,
            pg_transaction_id=f"DUMMY-{secrets.token_hex(8)}",
            pg_provider="MOCK_PG",
            status="SUCCESS",
            paid_at=datetime.utcnow(),
        )
        session.add(payment)

        cart.status = "COMPLETED"
        await session.commit()

        return {
            "ok": True,
            "order_id": order.id,
            "order_number": order.order_number,
            "order_type": order.order_type,
            "table_number": order.table_number,
            "subtotal": float(subtotal),
            "discount_amount": float(discount_amount),
            "final_amount": float(final_amount),
            "payment_status": payment.status,
            "payment_method": payment.method,
        }


approve_payment_tool = StructuredTool.from_function(
    coroutine=_approve_payment,
    name="approve_payment",
    description=(
        "현재 세션의 장바구니를 주문(ORDERS)으로 확정하고 결제(PAYMENTS)를 승인한다. "
        "사용자가 결제 의사를 명확히 표현한 후에만 호출하라. "
        "성공 시 order_number 와 final_amount 를 사용자에게 안내해야 한다."
    ),
    args_schema=ApprovePaymentArgs,
)


TOOLS = [search_menu_tool, add_to_cart_tool, get_cart_tool, approve_payment_tool]
