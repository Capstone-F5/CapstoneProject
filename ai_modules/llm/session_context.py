"""
요청별 세션 식별자/주문유형을 tool 안에서 읽기 위한 ContextVar.

엔드포인트(/ai_modules/llm) 진입 시 set, tools (add_to_cart, approve_payment, confirm_order) 가 get.
"""
from __future__ import annotations

from contextvars import ContextVar


_session_id: ContextVar[str] = ContextVar("kiosk_session_id", default="")
_order_type: ContextVar[str | None] = ContextVar("kiosk_order_type", default=None)


def set_session_id(sid: str) -> None:
    _session_id.set(sid)


def get_session_id() -> str:
    sid = _session_id.get()
    if not sid:
        raise RuntimeError("세션 ID 가 설정되지 않았습니다.")
    return sid


def set_order_type(order_type: str | None) -> None:
    """현재 화면에서 선택된 주문유형('dine-in'|'takeout'|None)을 요청 단위로 저장.

    confirm_order 툴이 이 값을 읽어 실제로 확정된 주문유형을 백엔드에 전달한다.
    (이전엔 이 값이 어디에도 저장되지 않아 음성 주문 확정 시 항상 기본값(TAKE_OUT)으로
    생성되던 버그가 있었음.)
    """
    _order_type.set(order_type)


def get_order_type() -> str | None:
    return _order_type.get()
