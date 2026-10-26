"""알레르기 질의를 코드로 답한다.

모델이 알레르기 질의에 자유롭게 답하면 틀린다(2026-10-06: "갑각류 알레르기 버거 없음"이라 했으나 새우·게살 버거가 있음,
대두 알레르기 손님에게 대두가 든 F 버거 세트를 추천). 메뉴 DB의 allergens(code)를 직접 읽어 계산한다.
순수 함수 위주라 API·LLM 없이 테스트할 수 있다.
"""
from __future__ import annotations

import re

_KEYWORD = re.compile(r"알레르기|알러지|알레르겐|알러젠|allerg", re.IGNORECASE)

# 성분 이름·코드는 DB(allergens 테이블)가 기준이다 — master = {code: name_ko}를 호출하는 쪽이 /api/menu/allergens에서 받아 넘긴다.
# 코드에 두는 것은 DB에 없는 정보뿐이다: 손님이 쓰는 묶음·동의어("갑각류"=새우+게, "계란"=난류). 대상 코드가 master에 없으면 무시한다.
_SYNONYMS: list[tuple[str, tuple[str, ...]]] = [
    ("갑각류", ("SHRIMP", "CRAB")), ("콩", ("SOY",)), ("유제품", ("MILK",)), ("유당", ("MILK",)), ("락토스", ("MILK",)),
    ("치즈", ("MILK",)), ("계란", ("EGG",)), ("달걀", ("EGG",)), ("밀가루", ("WHEAT",)), ("글루텐", ("WHEAT",)),
    ("조개", ("SHELLFISH",)), ("아황산", ("SULFITE",)), ("닭", ("CHICKEN",)), ("소고기", ("BEEF",)), ("돼지", ("PORK",)),
]
_HANGUL = r"가-힣"
_ALLERGY_AFTER = r"(?=\s*(?:알레르기|알러지))"


def _term_re(term: str) -> re.Pattern:
    # 한 글자 이름("게")은 오탐이 많아 "게 알레르기"처럼 뒤에 알레르기라는 말이 올 때만 인정한다
    tail = _ALLERGY_AFTER if len(term) == 1 else ""
    return re.compile(rf"(?<![{_HANGUL}]){re.escape(term)}{tail}")


_sessions: dict[str, set[str]] = {}


def extract_codes(text: str, master: dict[str, str]) -> set[str]:
    """발화에서 알레르기 성분 코드를 뽑는다. "알레르기"라는 말이 있어야 하고, 성분을 못 찾으면 빈 집합.
    master: {code: name_ko} (DB의 allergens 테이블)."""
    if not text or not master or not _KEYWORD.search(text):
        return set()
    found: set[str] = set()
    for code, name in master.items():
        if name and _term_re(name).search(text):
            found.add(code)
    for term, codes in _SYNONYMS:
        if _term_re(term).search(text):
            found.update(c for c in codes if c in master)
    return found


# ── 있다/없다 판단 ─────────────────────────────────────────────────────────────────────────────
# "갑각류 알레르기 없어"를 "있다"로 읽으면 안 된다(없다는 손님의 주문을 막는다). 규칙은 단순한 경우만 직접 판단하고,
# 있다/없다가 섞였거나 성분을 못 찾겠으면 LLM이 마스터 코드로 변환한다. 집합 계산(어떤 메뉴에 들었나)은 항상 코드·DB가 한다.
_NEG = re.compile(r"없|아니|괜찮|상관|무관|안\s*있")
_AFFIRM = re.compile(r"있|때문|못\s*먹|안\s*돼|안돼|안\s*되|걸려|반응|민감")


class Decision:
    """kind: have(규칙이 확정, codes 사용) | none(알레르기 없음/무관 — 기억·응답 안 함) | llm(LLM에 해석을 맡김)"""
    __slots__ = ("kind", "codes")

    def __init__(self, kind: str, codes: set[str] | None = None):
        self.kind, self.codes = kind, codes or set()


def decide(text: str, master: dict[str, str]) -> Decision:
    if not text or not _KEYWORD.search(text):
        return Decision("none")
    codes = extract_codes(text, master)
    neg, affirm = bool(_NEG.search(text)), bool(_AFFIRM.search(text))
    if codes:
        if not neg:
            return Decision("have", codes)
        return Decision("llm") if affirm else Decision("none")   # "갑각류 알레르기 없어" → 기억하지 않는다
    # 성분을 못 찾았다: "알레르기 없는 메뉴 알려줘"는 건너뛰고, 있다고 하는데 이름을 못 알아들은 경우("각광료")만 LLM에 묻는다
    return Decision("llm") if (affirm or not neg) else Decision("none")


def build_llm_prompt(text: str, master: dict[str, str]) -> str:
    listing = "\n".join(f"- {code}: {name}" for code, name in master.items())
    return (
        "손님이 키오스크에서 알레르기에 대해 말했다. 아래 알레르기 성분 목록의 code만 사용해 분류하라.\n"
        "have: 손님이 알레르기가 있다고 한 성분 / none: 알레르기가 없다고 하거나 무관하다고 한 성분.\n"
        "'갑각류'는 SHRIMP와 CRAB 등 해당하는 코드 전부, '계란'은 EGG처럼 목록의 가장 가까운 코드로 바꿔라. "
        "음성 인식 오류로 보이면 가장 그럴듯한 성분으로 고쳐라. 목록에 없는 성분은 넣지 마라. 추측이 약하면 비워 둬라.\n"
        f"성분 목록:\n{listing}\n\n손님 말: {text}\n\n"
        'JSON만 출력: {"have": ["CODE"], "none": ["CODE"]}'
    )


def parse_llm_answer(raw: str, master: dict[str, str]) -> set[str] | None:
    """LLM 응답에서 have 코드만 뽑는다. 마스터에 없는 코드는 버리고, JSON이 아니면 None."""
    import json
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    have = data.get("have") if isinstance(data, dict) else None
    if not isinstance(have, list):
        return None
    return {c for c in have if isinstance(c, str) and c in master}


async def resolve(text: str, master: dict[str, str], ask) -> set[str]:
    """규칙 판단 + (필요하면) LLM 해석으로 손님이 "있다"고 한 성분 코드를 돌려준다. 없으면 빈 집합.
    ask: async (prompt) -> str. 실패(타임아웃·잘못된 응답)는 빈 집합 = 모르는 것으로 처리한다."""
    d = decide(text, master)
    if d.kind == "have":
        return d.codes
    if d.kind == "none":
        return set()
    try:
        return parse_llm_answer(await ask(build_llm_prompt(text, master)), master) or set()
    except Exception:  # noqa: BLE001
        return set()


def remember(session_id: str, codes: set[str]) -> None:
    if session_id and codes:
        _sessions.setdefault(session_id, set()).update(codes)


def recall(session_id: str) -> set[str]:
    return set(_sessions.get(session_id, set()))


def reset(session_id: str) -> None:
    _sessions.pop(session_id, None)


def _item_codes(item: dict) -> set[str]:
    return {a.get("code") for a in item.get("allergens") or [] if a.get("code")}


def _label(codes: set[str], master: dict[str, str]) -> str:
    return "·".join(master.get(c, c) for c in master if c in codes) or "·".join(sorted(codes))


def unsafe_items(menu: list[dict], codes: set[str]) -> list[dict]:
    return [i for i in menu if i.get("is_available", True) and _item_codes(i) & codes]


def hits_for_item(item: dict, codes: set[str]) -> set[str]:
    return _item_codes(item) & codes


def _join(names: list[str], limit: int = 6) -> str:
    if len(names) > limit:
        return ", ".join(names[:limit]) + f" 등 {len(names)}가지"
    return ", ".join(names)


def build_reply(menu: list[dict], codes: set[str], master: dict[str, str]) -> str:
    """알레르기 성분(codes)을 가진 손님에게 먹을 수 없는 메뉴와 괜찮은 메뉴를 말하듯이 안내한다."""
    avail = [i for i in menu if i.get("is_available", True)]
    bad = unsafe_items(avail, codes)
    bad_ids = {i["id"] for i in bad}
    good = [i for i in avail if i["id"] not in bad_ids]
    label = _label(codes, master)
    if not bad:
        text = f"{label} 알레르기 성분이 들어간 메뉴는 없어요."
    else:
        text = f"{label} 알레르기가 있으시면 {_join([i['name_ko'] for i in bad])}는 드실 수 없어요."
        if good:
            text += f" 나머지로는 {_join([i['name_ko'] for i in good])} 등이 괜찮아요."
    return text + " 조리 과정에서 섞일 수 있으니 심하시면 직원에게도 꼭 확인해 주세요."


def warning_for_add(item: dict, codes: set[str]) -> str | None:
    """손님이 밝힌 알레르기 성분이 담으려는 메뉴에 들어 있으면 거절 메시지를, 아니면 None."""
    hit = hits_for_item(item, codes)
    if not hit:
        return None
    names = "·".join(a["name_ko"] for a in item.get("allergens") or [] if a.get("code") in hit)   # 이름은 메뉴 API(DB)가 준 것
    return (f"오류: 손님이 {names} 알레르기가 있다고 했는데 '{item['name_ko']}'에 {names} 성분이 들어 있습니다. "
            f"담지 말고, 알레르기 때문에 드실 수 없다고 알려 준 뒤 다른 메뉴를 권하세요.")
