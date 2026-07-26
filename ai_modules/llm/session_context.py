"""
요청별 세션 식별자를 tool 안에서 읽기 위한 ContextVar.

엔드포인트(/ai_modules/llm) 진입 시 set, tools 가 get.
"""
from __future__ import annotations

from contextvars import ContextVar


_session_id: ContextVar[str] = ContextVar("kiosk_session_id", default="")


def set_session_id(sid: str) -> None:
    _session_id.set(sid)


def get_session_id() -> str:
    sid = _session_id.get()
    if not sid:
        raise RuntimeError("세션 ID 가 설정되지 않았습니다.")
    return sid
