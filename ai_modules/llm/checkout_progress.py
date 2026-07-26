"""
세션별 결제 단계 진행 상태 — 요청(턴)을 넘어 지속되는 서버 쪽 실제 상태.

action_context.py의 ContextVar들은 "이번 요청 한 번"만 유지되는 반면, 여기 상태는 모듈
전역 dict에 저장돼 다음 턴에도 남는다. 목적은 "포인트 적립 여부를 먼저 반드시 물어야 한다"
같은 순서 규칙을 프롬프트 지시문이 아니라 코드가 직접 강제하는 것 — 프롬프트 문구만으로는
gpt-4o-mini가 한 턴 안에서 다음 단계를 스스로 앞질러 호출해버리는 사례가 재현되어(재현 테스트로
확인) 순서를 프롬프트만으로 보장할 수 없었다.

핵심 규칙: 어떤 단계가 "완료됐다"고 인정되는 건 그 단계가 실행된 턴 *이전에* 이미 완료돼
있었을 때뿐이다. 같은 턴 안에서 A를 호출한 직후 곧바로 B를 호출해도, B 시점에는 A가
"이번 턴에 방금" 끝난 것이므로 인정하지 않는다 — 이렇게 해야 한 턴 안에서 여러 단계를
한꺼번에 앞질러 완주해버리는 것을 막을 수 있다.
"""
from __future__ import annotations

_done: dict[str, set[str]] = {}


def snapshot(session_id: str) -> frozenset[str]:
    """이번 턴 시작 시점의 완료 단계 스냅샷. llm_service.py가 턴 시작 시 1회 호출."""
    return frozenset(_done.get(session_id, set()))


def mark_done(session_id: str, step: str) -> None:
    """단계 완료를 영구 기록(다음 턴부터 snapshot에 반영됨)."""
    _done.setdefault(session_id, set()).add(step)


def was_done_before_this_turn(before_turn: frozenset[str], step: str) -> bool:
    return step in before_turn


def reset(session_id: str) -> None:
    """새 주문이 시작될 때(장바구니 비우기 등) 이전 주문의 결제 진행 상태를 지운다."""
    _done.pop(session_id, None)
