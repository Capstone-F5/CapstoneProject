"""
요청별 장바구니 스냅샷과 발행된 액션을 tool 안에서 읽기 위한 ContextVar.

엔드포인트(/ai_modules/llm/stream) 진입 시:
  set_cart(cart)   — 요청 body 의 장바구니 스냅샷 저장
  reset_actions()  — 이전 요청 잔여 액션 초기화
tools 안에서:
  get_cart()       — 현재 장바구니 조회
  push_action(d)   — 액션 발행
스트림 종료 후:
  get_actions()    — 모인 액션 목록 회수 → SSE 로 전송
"""
from __future__ import annotations

from contextvars import ContextVar


_cart: ContextVar[list] = ContextVar("kiosk_cart", default=[])
_actions: ContextVar[list] = ContextVar("kiosk_actions", default=[])


def set_cart(cart: list) -> None:
    _cart.set(cart)


def get_cart() -> list:
    return _cart.get()


def reset_actions() -> None:
    # 새 리스트를 set 해야 이전 요청 잔여가 남지 않는다
    _actions.set([])


def push_action(action: dict) -> None:
    _actions.get().append(action)


def get_actions() -> list:
    return _actions.get()