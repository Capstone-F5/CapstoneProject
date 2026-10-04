"""세션별 직전 담기·삭제 기록 — "방금 담은 거 취소해줘", "아까 뺀 거 다시 담아줘"를 코드가 처리하기 위한 서버 쪽 상태.

장바구니(DB)에는 무엇이 "방금" 담겼는지가 남지 않는다. 도구가 담기·삭제에 성공할 때마다 여기에 적어 두고,
직접 명령 처리(core/cart_commands.py)가 읽는다. checkout_progress.py와 같은 모듈 전역 dict 방식이다.
"""
from __future__ import annotations

from ai_modules.llm import checkout_progress

_turn: dict[str, int] = {}
_added: dict[str, tuple[int, list[dict]]] = {}   # 세션 → (턴 번호, 그 턴에 담은 줄들)
_removed: dict[str, tuple[int, list[dict]]] = {}   # 세션 → (턴 번호, 그 턴에 지운 줄들)


def begin_turn(session_id: str) -> None:
    """새 발화가 시작될 때 호출. 한 발화에서 여러 품목을 담았으면 한꺼번에 되돌리기 위해 턴을 구분한다."""
    _turn[session_id] = _turn.get(session_id, 0) + 1


def record_added(session_id: str, cart_item_id: str, name: str, qty: int, via: str = "add") -> None:
    """이번 턴에 cart_item_id 줄에 qty개를 더했다고 기록한다(기존 줄에 합쳐진 경우도 늘어난 수량만 적는다)."""
    # 결제를 시작한 뒤 품목이 늘면 손님은 메뉴로 돌아간 것이다 — 다음 "결제할게요"에서 포인트 질문부터 다시 한다
    checkout_progress.reset(session_id)
    turn = _turn.get(session_id, 0)
    entry = {"cart_item_id": cart_item_id, "name": name, "qty": int(qty), "via": via}
    cur = _added.get(session_id)
    if cur and cur[0] == turn:
        cur[1].append(entry)
    else:
        _added[session_id] = (turn, [entry])


def pop_added(session_id: str) -> list[dict]:
    cur = _added.pop(session_id, None)
    return cur[1] if cur else []


def peek_added(session_id: str, this_turn_only: bool = False) -> list[dict]:
    cur = _added.get(session_id)
    if not cur or (this_turn_only and cur[0] != _turn.get(session_id, 0)):
        return []
    return cur[1]


def record_removed(session_id: str, line: dict) -> None:
    """지운 줄(장바구니 API의 항목)을 다시 담을 수 있는 형태로 기록한다. 한 발화에서 여러 줄을 지웠으면 모두 남긴다."""
    entry = {
        "menu_item_id": line.get("menu_item_id"),
        "name": line.get("name_ko", ""),
        "quantity": int(line.get("quantity", 1)),
        "selected_options": [{"option_id": o["option_id"], "name": o.get("name", "")}
                             for o in line.get("selected_options", [])],
        "special_note": line.get("special_note"),
    }
    turn = _turn.get(session_id, 0)
    cur = _removed.get(session_id)
    if cur and cur[0] == turn:
        cur[1].append(entry)
    else:
        _removed[session_id] = (turn, [entry])


def pop_removed(session_id: str) -> list[dict]:
    cur = _removed.pop(session_id, None)
    return cur[1] if cur else []


def peek_removed(session_id: str) -> list[dict]:
    cur = _removed.get(session_id)
    return cur[1] if cur else []


def reset(session_id: str) -> None:
    _added.pop(session_id, None)
    _removed.pop(session_id, None)
