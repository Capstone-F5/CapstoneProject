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


#  세션 ID 전역 관리 스토리지 추가
_session_id: str = "default"

def set_session_id(sid: str) -> None:
    """FastAPI 진입점에서 사용자의 session_id를 주입하기 위한 함수"""
    global _session_id
    _session_id = sid

def get_session_id() -> str:
    """action_tools.py 내 Tool들이 현재 세션 ID를 조회하기 위한 함수"""
    return _session_id