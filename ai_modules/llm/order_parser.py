"""문장이 "메뉴 이름 + 수량 (+ 단품)"뿐인 단순 주문일 때 코드가 직접 풀어 내는 규칙 파서 — 순수 함수, LLM 없음.

모델이 도구를 부르지 않고 "메뉴에 없습니다"라고 답하거나(실제로는 있는 메뉴), "담았습니다"라고만 하거나,
이미 "단품"이라고 말했는데 또 되묻는 사고가 다품목 주문에서 자주 났다. 이런 경우 손님이 무엇을 몇 개 달라고
했는지가 문장에서 하나로 정해지면 코드가 그대로 담는다. 조금이라도 불확실하면(모르는 말이 남거나, 세트이거나,
버거에 단품 표시가 없거나, 이름이 여럿으로 겹치면) None을 돌려 아무것도 하지 않는다 — "모르면 막지 않는다".
"""
from __future__ import annotations

import re

from ai_modules.llm import guards


def menu_key(name: str) -> str:
    """메뉴 이름을 비교용으로 정규화한다(공백·괄호 설명 제거)."""
    return re.sub(r"\s+", "", (name or "").split("(")[0])


def named_menus(compact: str, names: list[str]) -> list[str]:
    """붙여 쓴 문장에서 언급된 메뉴 이름을 돌려준다. 긴 이름부터 찾아 지워서
    "더블 치즈 버거"를 말했을 때 "치즈 버거"까지 같이 걸리는 일을 막는다."""
    found: list[str] = []
    rest = compact
    for n in sorted(names, key=lambda x: -len(menu_key(x))):
        key = menu_key(n)
        if len(key) >= 2 and key in rest:
            found.append(n)
            rest = rest.replace(key, " ")
    return found


_SPLIT = re.compile(r"그리고|이랑|하고|랑|,|·|\s및\s|와(?=\s*[가-힣])|과(?=\s*[가-힣])")
_QTY_STRIP = re.compile(r"\d+\s*(?:개|잔|조각|판|명)|하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열\s*(?:개|잔)|(?:한|두|세|네)\s*(?:개|잔|조각|판)")
_FILLER = re.compile(
    r"단품(?:으로)?|그냥|주세요|줄래요?|줘요?|담아\s*주세요|담아줘요?|담아|추가(?:해|할게|해줘|해주세요|할게요)?|해줘|해주세요|"
    r"부탁(?:해요|드려요|합니다)?|주문(?:할게요?|해요)?|할게요?|씩|각각|도|를|을|이|가|은|는|으로|로|좀|만|요|어|음|저기|저|아|잠깐|잠시|그럼|네|예|응|"
    r"[ \t.,!?~]+"
)


def _resolve(name: str, menu: list[dict]) -> dict | None:
    key = menu_key(name)
    hits = [i for i in menu if menu_key(i["name_ko"]) == key]
    return hits[0] if len(hits) == 1 else None


_QTY_TOKEN = re.compile(r"\d+\s*(?:개|잔|조각|판)|(?:한|두|세|네|다섯|여섯)\s*(?:개|잔|조각|판)|하나")


def _split_after_quantity(text: str, names: list[str]) -> str:
    """"치즈 버거 단품 한개 콜라 한잔"처럼 구분어 없이 이어 말한 주문을 항목별로 나눈다. 수량 표현 바로 뒤에 다른 메뉴 이름이
    이어질 때만 쉼표를 넣는다("치즈버거 하나 줘"의 "하나 줘"는 나누지 않는다)."""
    keys = sorted({menu_key(n) for n in names if len(menu_key(n)) >= 2}, key=len, reverse=True)
    out, last = [], 0
    for m in _QTY_TOKEN.finditer(text):
        rest = re.sub(r"\s+", "", text[m.end():])
        if any(rest.startswith(k) for k in keys):
            out.append(text[last:m.end()])
            last = m.end()
    out.append(text[last:])
    return ",".join(out)


def parse_simple_order(text: str, menu: list[dict]) -> list[tuple[dict, int]] | None:
    """[(메뉴 항목, 수량), ...]을 돌려준다. 단순 주문으로 확신할 수 없으면 None."""
    if not text or not menu or not guards.has_hangul(text):
        return None
    if guards.mentions_set(text) or guards.is_question_only(text) or guards.has_remove_intent(text):
        return None
    burgers = [i["name_ko"] for i in menu if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    names = [i["name_ko"] for i in menu]
    segments = [s.strip() for s in _SPLIT.split(_split_after_quantity(text, names)) if s and s.strip()]
    if not segments:
        return None
    whole_burgers = named_menus(re.sub(r"\s+", "", text), burgers)
    out: list[tuple[dict, int]] = []
    seen: set[str] = set()
    for seg in segments:
        compact = re.sub(r"\s+", "", seg)
        found = named_menus(compact, names)
        if len(found) != 1:
            return None
        item = _resolve(found[0], menu)
        if item is None or item["id"] in seen:
            return None
        seen.add(item["id"])
        # 이름·수량·단품·군더더기를 지우고 남는 말이 있으면 단순 주문이 아니다
        rest = compact.replace(menu_key(found[0]), "")
        rest = _QTY_STRIP.sub("", rest)
        rest = _FILLER.sub("", rest)
        if len(rest) > 1:
            return None
        qty = guards.quantity_in(seg)
        if qty is None:
            if _QTY_STRIP.search(compact):
                return None   # 수량 표현이 여럿이거나 모호하다
            qty = 1
        if found[0] in burgers:
            explicit = guards.mentions_single(seg) or (len(whole_burgers) == 1 and guards.mentions_single(text))
            if not explicit:
                return None   # 버거는 단품이라고 분명히 말했을 때만(아니면 단품/세트를 되묻는 것이 설계)
        out.append((item, qty))
    return out or None


_CLAIM_SENTENCE = re.compile(r"담았(?:습니다|어요|죠)|추가했(?:습니다|어요)|담겠습니다|담아\s*드리겠습니다|추가하겠습니다|추가해\s*드리겠습니다")


def parse_claimed_add(output: str, menu: list[dict]) -> list[tuple[dict, int]] | None:
    """모델이 "X 단품을 담겠습니다/담았습니다"라고 했을 때 그 품목. 메뉴 하나가 분명하고, 버거라면 "단품"이라고 적혀 있을 때만
    돌려준다(세트·여러 메뉴·애매하면 None). 도구를 부르지 않은 채 말로만 약속한 주문을 코드가 지킬 때 쓴다."""
    burgers = [i["name_ko"] for i in menu if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    for sent in re.split(r"(?<=[.!?])\s*", output or ""):
        if not _CLAIM_SENTENCE.search(sent):
            continue
        found = named_menus(re.sub(r"\s+", "", sent), [i["name_ko"] for i in menu])
        if len(found) != 1 or guards.mentions_set(sent):
            return None
        item = _resolve(found[0], menu)
        if item is None or (found[0] in burgers and not guards.mentions_single(sent)):
            return None
        return [(item, guards.quantity_in(sent) or 1)]
    return None


def claimed_burger_without_type(output: str, menu: list[dict]) -> str | None:
    """응답이 버거 하나를 "담겠습니다/담았습니다"라고 하면서 단품/세트를 말하지 않았으면 그 버거 이름(손님이 단품/세트를
    말하지 않았으니 먼저 물어야 하는 경우)."""
    burgers = [i["name_ko"] for i in menu if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    for sent in re.split(r"(?<=[.!?])\s*", output or ""):
        if not _CLAIM_SENTENCE.search(sent):
            continue
        found = named_menus(re.sub(r"\s+", "", sent), [i["name_ko"] for i in menu])
        if len(found) == 1 and found[0] in burgers and not guards.mentions_set(sent) and not guards.mentions_single(sent):
            return found[0]
        return None
    return None


def burger_only_order(text: str, menu: list[dict]) -> str | None:
    """문장이 "버거 하나 줘"처럼 버거 이름 하나(+수량·군더더기)뿐이고 단품/세트·"더"·추가·질문이 없으면 그 버거 이름.
    (이 경우 키오스크는 단품/세트를 물어야 한다)"""
    if (not text or guards.mentions_single(text) or guards.mentions_set(text) or guards.is_question_only(text)
            or guards.has_remove_intent(text) or not guards.has_hangul(text)):
        return None
    burgers = [i["name_ko"] for i in menu if any(o.get("option_group") == "SET_UPGRADE" for o in i.get("options") or [])]
    compact = re.sub(r"\s+", "", text)
    found = named_menus(compact, [i["name_ko"] for i in menu])
    if len(found) != 1 or found[0] not in burgers:
        return None
    rest = _FILLER.sub("", _QTY_STRIP.sub("", compact.replace(menu_key(found[0]), "")))
    if rest or not guards.has_add_verb(text) or re.search(r"더\s*(?:줘|주세요|담|추가)|더\s*$|추가|또\s", text):
        return None
    return found[0]


# ── 모델이 하지 못한 일을 알아보는 응답 패턴 ───────────────────────────────────
_CLAIM_UNAVAILABLE = re.compile(
    r"메뉴에\s*없|찾을\s*수\s*없|품절|판매하지\s*않|제공하지\s*않|취급하지\s*않|주문할\s*수\s*없|"
    r"문제가\s*발생|계속\s*문제|찾는\s*데|추가하는\s*데|담는\s*데")
# 손님이 이미 분명히 주문했는데 되묻거나("담아드릴까요?") 하겠다고만("담겠습니다") 하고 도구를 부르지 않은 경우도 포함한다
_ASKS_SINGLE_SET = re.compile(
    r"단품으로\s*(?:드릴까요|담을까요|담아\s*드릴까요)|세트로\s*(?:드릴까요|담을까요|담아\s*드릴까요)|"
    r"담아\s*드릴까요|담을까요|담겠습니다|추가하겠습니다|추가로\s*담")


def reply_failed_to_act(output: str) -> str | None:
    """모델이 손님이 말한 주문을 처리하지 않았다는 신호가 응답에 있으면 그 종류를 돌려준다."""
    if guards.claims_add(output):
        return "claimed_add"
    if _CLAIM_UNAVAILABLE.search(output or ""):
        return "claimed_unavailable"
    if _ASKS_SINGLE_SET.search(output or ""):
        return "asked_single_set"
    return None


_AWAITING_SET_OPTION = re.compile(r"사이드|음료|뭘로|뭐로|어떤\s*걸로|어떤\s*것으로")


def awaiting_set_option(last_bot: str) -> bool:
    """직전 안내가 세트의 사이드·음료를 고르라고 묻는 중인가. 그렇다면 손님이 "콜라로 주세요"라고 해도 그것은
    단품 주문이 아니라 세트 옵션 선택이다."""
    # 사이드·음료를 묻는 질문 문장이 있어야 한다("사이드 …, 음료 … 담았습니다"라는 확인 문구는 아니다)
    sentences = re.split(r"(?<=[.!?])\s+", (last_bot or "").strip())
    return any("?" in s and _AWAITING_SET_OPTION.search(s) for s in sentences)


def confirmation_text(added: list[tuple[dict, int]]) -> str:
    parts = ", ".join(f"{i['name_ko']} {q}개" for i, q in added)
    return f"{parts} 담았습니다. 다른 메뉴를 더 주문하시겠어요?"
