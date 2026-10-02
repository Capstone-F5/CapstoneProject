"""AI를 거치지 않는 규칙 기반 가드 모음 — 순수 함수만 둔다(부수효과·네트워크 없음).

LLM이 손님 말과 다르게 행동하거나, 음성 인식(STT)이 틀리게 받아 적은 것을 코드로 바로잡는다.
판정에 LLM을 쓰지 않으므로 추가 API 비용이 들지 않고, 단위 테스트(backend/tests/test_guards.py)가 비용 없이 돈다.

지금 들어 있는 것
- fix_stt: 로그에서 확인된 STT 오인식을 문맥 조건부로 교정
"""
from __future__ import annotations

import re

# ── STT 오인식 교정표 ─────────────────────────────────────────────────────────
# (패턴, 치환). 문맥 조건을 붙여 다른 뜻의 문장을 건드리지 않는다. 항목을 늘릴 때는 tests에 "교정되는 말"과
# "그대로여야 하는 말"을 함께 넣을 것. 메뉴 이름처럼 다른 메뉴로 잘못 바꿀 위험이 있는 것("엠투버거" 등)은
# 자동 교정하지 않는다.
_STT_FIXES: list[tuple[re.Pattern, str]] = [
    # "매장에서 먹을게요"가 "내장에서 먹을게요"로 들어오는 경우(실제 로그). 뒤에 식사·주문 어휘가 올 때만.
    (re.compile(r"내장(?=\s*에서\s*(?:먹|드|식사|할|해|줘|주문))"), "매장"),
    # "매장 식사로 할게요" → "내장 식사로 할게요", "매장이요" → "내장이요"
    (re.compile(r"내장(?=\s*(?:식사|이요|으로\s*(?:할|해|줘|먹)))"), "매장"),
]


def fix_stt(text: str) -> str:
    """알려진 STT 오인식을 교정한 문장을 돌려준다. 해당 부분만 바꾸고 나머지는 그대로 둔다."""
    if not text:
        return text
    fixed = text
    for pattern, repl in _STT_FIXES:
        fixed = pattern.sub(repl, fixed)
    return fixed
