"""
음성/텍스트 대화 턴을 JSONL로 기록 — 나중에 테스트 시나리오로 재사용하기 위한 로그.

한 턴 = 한 줄(JSON). backend/logs/conversations/ 아래 날짜별 파일(YYYY-MM-DD.jsonl)로
나뉜다. 로그는 부가 기능이지 핵심 대화 경로가 아니므로, 기록 자체가 실패해도
조용히 무시하고 실제 응답 흐름을 절대 막지 않는다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from ai_modules.llm.action_context import get_guard_hits, get_stt_original

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "conversations")


def log_turn(
    *,
    session_id: str,
    user_input: str,
    output: str,
    actions: list,
    language: str | None = None,
    screen: str | None = None,
    order_type: str | None = None,
    error: str | None = None,
) -> None:
    try:
        now = datetime.now(timezone.utc)
        os.makedirs(_LOG_DIR, exist_ok=True)
        path = os.path.join(_LOG_DIR, f"{now.strftime('%Y-%m-%d')}.jsonl")
        record = {
            "timestamp": now.isoformat(),
            "session_id": session_id,
            "screen": screen,
            "order_type": order_type,
            "language": language,
            "input": user_input,
            "output": output,
            "actions": actions,
            "error": error,
        }
        hits = get_guard_hits()
        if hits:
            record["guards"] = hits   # 규칙 가드가 개입한 기록(어떤 규칙이, 왜)
        original = get_stt_original()
        if original:
            record["stt_original"] = original   # STT 교정 전 원문(어떤 오인식이 자주 나오는지 보려고)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
