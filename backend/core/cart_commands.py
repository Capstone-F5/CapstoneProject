"""LLM을 거치지 않고 코드가 직접 처리하는 장바구니 명령 — 문장 모양이 분명할 때만(모르면 None → 평소대로 LLM).

모델이 이런 문장에서 도구를 잘못 부르거나(메뉴 id 자리에 이름, 사이드·음료를 별도 품목으로 담음, 줄 전체 삭제,
옵션 중복 변경) 안 부르고 말만 하는 사고가 실측(고정 100개 시나리오)에서 반복돼, 문법이 정해진 말만 규칙으로 처리한다.
  - "방금 담은 거 취소해줘" / "아까 뺀 X 다시 담아줘"   (cart_history 기록 사용)
  - "X 세트 두 개, 사이드는 A 음료는 B로 줘"          (세트 한 번에 담기)
  - "X 단품을 세트로 바꿔줘. 사이드는 A 음료는 B"     (단품 → 세트)
  - "X 세트 말고 단품으로 바꿔줘"                      (세트 → 단품)
  - "X 세트 사이드는 A 음료는 B로 바꿔줘"             (세트 옵션 변경)
  - "X 단품 하나만 빼줘 / 한 개 줄여줘"               (수량 1 감소)
  - "X 단품 전부 빼줘 / 지워줘 / 취소해줘"            (줄 삭제)
개입은 가드 기록(record_guard "direct_command")으로 남는다. 판정에 LLM을 쓰지 않아 추가 비용이 없다.
"""
from __future__ import annotations

import re

from ai_modules.llm import api_client, cart_history, guards
from ai_modules.llm.action_context import push_action, record_guard
from ai_modules.llm.order_parser import _FILLER, _QTY_STRIP, menu_key, named_menus

_UNDO = re.compile(r"(?:방금|아까|조금\s*전)\s*(?:담은|추가한|넣은|주문한)\s*(?:거|것|걸|건|메뉴)?\s*(?:좀\s*)?(?:취소|빼|지워|삭제|도로)")
_READD = re.compile(r"(?:아까|방금)\s*(?:뺀|뺐던|지운|지웠던|삭제한|취소한)\s*(?P<what>.*?)\s*(?:다시|도로)\s*(?:담아|추가|넣어|주문)")
_VAGUE = {"", "거", "것", "걸", "건", "그거", "그것", "그걸", "메뉴"}
_SIDE = re.compile(r"사이드(?:는|를|을|로)?\s*(?P<v>[가-힣]+?)(?:으로|로)?\s*(?=음료|[,.]|바꿔|변경|해\s*줘|해줘|$)")
_DRINK = re.compile(r"음료(?:수)?(?:는|를|을|로)?\s*(?P<v>[가-힣]+?)(?:으로|로)?\s*(?=[,.]|줘|주세요|바꿔|변경|해\s*줘|해줘|할게|$)")
_TO_SET = re.compile(r"단품(?:을|를)?\s*세트(?:로)?\s*(?:바꿔|변경|해)")
_TO_SINGLE = re.compile(r"세트\s*(?:말고|아니고)\s*단품(?:으로)?\s*(?:바꿔|변경|해)")
_CHANGE = re.compile(r"바꿔|바꾸|변경")
_NO_NEW_ORDER = re.compile(r"바꿔|바꾸|변경|말고|빼|취소|삭제|지워|그만")
_SET_NAMES = ("SET_UPGRADE", "SET_SIDE", "SET_DRINK")
_KEEP_N = re.compile(r"(?:하나|한\s*개|\d+\s*개|[두세네]\s*개)\s*만\s*남(?:겨|기)")
_REMOVE_VERB = re.compile(r"(?:빼|지워|취소|삭제)(?:해)?(?:줘|주세요)?요?")
_REMOVE_NOT_LINE = re.compile(r"빼고|제외|없이|방금|아까|다시")
_REMOVE_FILLER = re.compile(r"단품|세트|전부|모두|다|을|를|은|는|도|만|좀|[.,!?~]")


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _is_burger(item: dict) -> bool:
    return any(o.get("option_group") == "SET_UPGRADE" for o in item.get("options") or [])


def _one_named(text: str, items: list[dict]) -> dict | None:
    found = named_menus(_compact(text), [i["name_ko"] for i in items])
    return next((i for i in items if i["name_ko"] == found[0]), None) if len(found) == 1 else None


def _pick_option(item: dict, group: str, spoken: str) -> dict | None:
    """말한 사이드·음료 이름에 맞는 옵션 하나. 정확히 같은 이름을 먼저, 없으면 한 옵션에만 겹칠 때."""
    key = _compact(spoken)
    cands = [o for o in item.get("options") or [] if o.get("option_group") == group and o.get("is_available", True)]
    exact = [o for o in cands if _compact(o["name_ko"]) == key]
    if exact:
        return exact[0]
    # "너겟"처럼 짧아도 한 옵션에만 겹치면("치킨너겟") 그 옵션이다
    near = [o for o in cands if len(key) >= 2 and (key in _compact(o["name_ko"]) or _compact(o["name_ko"]) in key)]
    if len(near) > 1:
        longest = max(len(_compact(o["name_ko"])) for o in near)
        near = [o for o in near if len(_compact(o["name_ko"])) == longest]
    return near[0] if len(near) == 1 else None


def _spoken_options(text: str) -> tuple[str | None, str | None]:
    s, d = _SIDE.search(text), _DRINK.search(text)
    return (s.group("v") if s else None), (d.group("v") if d else None)


def parse_command(text: str, menu: list[dict]) -> dict | None:
    """문장이 위 문법 중 하나이고 대상이 하나로 정해질 때만 명령 dict를 돌려준다."""
    if not text or not menu or not guards.has_hangul(text):
        return None
    if _UNDO.search(text):
        return {"kind": "undo"}
    m = _READD.search(text)
    if m:
        return {"kind": "readd", "what": m.group("what").strip()}
    if guards.is_question_only(text):
        return None
    burgers = [i for i in menu if _is_burger(i)]
    burger = _one_named(text, burgers)
    side_w, drink_w = _spoken_options(text)

    if burger and _TO_SINGLE.search(text):
        return {"kind": "to_single", "item": burger}
    if burger and _TO_SET.search(text) and side_w and drink_w:
        return {"kind": "to_set", "item": burger, "side": side_w, "drink": drink_w}
    if burger and guards.mentions_set(text) and _CHANGE.search(text) and not re.search(r"말고|아니고", text) \
            and (side_w or drink_w):
        return {"kind": "set_options", "item": burger, "side": side_w, "drink": drink_w}
    if burger and guards.mentions_set(text) and side_w and drink_w and not _NO_NEW_ORDER.search(text):
        prefix = text[:min(text.find("사이드"), text.find("음료"))]   # 사이드·음료를 말했으니 둘 다 있다
        rest = _compact(prefix).replace(menu_key(burger["name_ko"]), "").replace("세트", "").replace("이번엔", "")
        rest = _FILLER.sub("", _QTY_STRIP.sub("", rest)).replace("더", "")
        if len(rest) <= 1:
            return {"kind": "set_order", "item": burger, "qty": guards.quantity_in(prefix) or 1,
                    "side": side_w, "drink": drink_w}
    if _REMOVE_VERB.search(text) and not guards.wants_reduce_one(text) and not _REMOVE_NOT_LINE.search(text):
        # "X 단품 전부 빼줘/지워줘/취소해줘" — 줄 하나를 통째로 지운다(재료 제외로 오해하는 모델 사고 방지).
        # 메뉴 이름·단품/세트·군더더기를 지우고 남는 말이 있으면("양파 빼줘") 줄 삭제가 아니다.
        target = _one_named(text, menu)
        if target:
            rest = _compact(text).replace(menu_key(target["name_ko"]), "")
            rest = _REMOVE_FILLER.sub("", _REMOVE_VERB.sub("", rest))
            if not rest:
                return {"kind": "remove_line", "item": target,
                        "is_set": True if guards.mentions_set(text) else (False if guards.mentions_single(text) else None)}
    if _KEEP_N.search(text):
        target = _one_named(text, menu)   # "치즈버거 하나만 남겨줘" — 합계를 그 수로 맞춘다
        if target and guards.quantity_in(text):
            return {"kind": "keep_n", "item": target, "n": guards.quantity_in(text),
                    "is_set": True if guards.mentions_set(text) else (False if guards.mentions_single(text) else None)}
    if guards.wants_reduce_one(text):
        target = _one_named(text, menu)
        if target:
            return {"kind": "reduce_one", "item": target,
                    "is_set": True if guards.mentions_set(text) else (False if guards.mentions_single(text) else None)}
    return None


def _is_set_line(line: dict, item: dict) -> bool:
    set_ids = {o["id"] for o in item.get("options") or [] if o.get("option_group") == "SET_UPGRADE"}
    return any(s["option_id"] in set_ids for s in line.get("selected_options", []))


def _lines_of(cart: dict, item: dict, is_set: bool | None = None) -> list[dict]:
    lines = [l for l in cart.get("items", []) if l.get("menu_item_id") == item["id"]]
    return lines if is_set is None else [l for l in lines if _is_set_line(l, item) == is_set]


def _same_options(lines: list[dict]) -> bool:
    """서버는 같은 메뉴·같은 옵션을 담아도 줄을 합치지 않는다 — 그런 줄들이면 하나의 품목으로 다룰 수 있다."""
    return len({tuple(sorted(s["option_id"] for s in l.get("selected_options", []))) for l in lines}) == 1


def _keep_non_set(line: dict, item: dict, drop: set[str]) -> list[dict]:
    group = {o["id"]: o.get("option_group") for o in item.get("options") or []}
    return [{"option_id": s["option_id"], "name": s.get("name", "")} for s in line.get("selected_options", [])
            if group.get(s["option_id"]) not in drop]


async def _reduce_total(session_id: str, lines: list[dict], by: int) -> None:
    """같은 품목의 줄들(서버는 합치지 않는다)에서 마지막 줄부터 합계를 by개 줄인다. 0이 된 줄은 지운다."""
    for line in reversed(lines):
        if by <= 0:
            break
        qty = int(line.get("quantity", 1))
        take = min(by, qty)
        by -= take
        if take == qty:
            await api_client.remove_cart_item(session_id, line["cart_item_id"])
            push_action({"type": "remove_item", "cart_item_id": line["cart_item_id"]})
        else:
            await api_client.patch_cart_item(session_id, line["cart_item_id"], {"quantity": qty - take})
            push_action({"type": "update_item", "cart_item_id": line["cart_item_id"], "quantity": qty - take})


async def execute(session_id: str, cmd: dict, menu: list[dict]) -> str | None:
    """명령을 실행하고 손님에게 할 말을 돌려준다. 실행할 수 없으면(대상 없음·재고 등) None → LLM이 이어받는다."""
    kind = cmd["kind"]
    cart = await api_client.get_cart(session_id)

    if kind == "undo":
        done = []
        lines = {l["cart_item_id"]: l for l in cart.get("items", [])}
        entries = cart_history.peek_added(session_id)
        if not entries or any(e["cart_item_id"] not in lines for e in entries):
            return None
        for e in reversed(entries):
            line = lines[e["cart_item_id"]]
            left = int(line.get("quantity", 1)) - e["qty"]
            if left > 0:
                await api_client.patch_cart_item(session_id, e["cart_item_id"], {"quantity": left})
                push_action({"type": "update_item", "cart_item_id": e["cart_item_id"], "quantity": left})
            else:
                await api_client.remove_cart_item(session_id, e["cart_item_id"])
                push_action({"type": "remove_item", "cart_item_id": e["cart_item_id"]})
            done.append(f"{e['name']} {e['qty']}개")
        cart_history.pop_added(session_id)
        return f"방금 담은 {', '.join(done)}를 취소했습니다. 다른 메뉴를 더 주문하시겠어요?"

    if kind == "readd":
        lines = cart_history.peek_removed(session_id)
        if not lines:
            return None
        what = _compact(cmd["what"])
        if what not in _VAGUE and not any(menu_key(l["name"]) in what for l in lines):
            return None   # 다른 메뉴를 가리킨다
        if what not in _VAGUE:
            lines = [l for l in lines if menu_key(l["name"]) in what]   # 말한 메뉴만 복원
        done = []
        for last in lines:
            res = await api_client.add_cart_item(session_id, {
                "menu_item_id": last["menu_item_id"], "quantity": last["quantity"],
                "selected_options": last["selected_options"], "special_note": last["special_note"]})
            cart_history.record_added(session_id, res.get("cart_item_id"), last["name"], last["quantity"])
            push_action({"type": "add_item", "menu_item_id": last["menu_item_id"], "name": last["name"],
                         "quantity": last["quantity"], "upgrade_to_set": False, "side": None, "drink": None,
                         "exclusions": [], "cart_item_id": res.get("cart_item_id")})
            done.append(f"{last['name']} {last['quantity']}개")
        cart_history.pop_removed(session_id)
        return f"{', '.join(done)}를 다시 담았습니다. 다른 메뉴를 더 주문하시겠어요?"

    item = await api_client.fetch_menu_item_by_id(cmd["item"]["id"])
    if not item or not item.get("is_available", True):
        return None
    name = item["name_ko"]

    if kind in ("set_order", "to_set", "set_options"):
        set_opt = next((o for o in item["options"] if o.get("option_group") == "SET_UPGRADE"), None)
        side = _pick_option(item, "SET_SIDE", cmd["side"]) if cmd.get("side") else None
        drink = _pick_option(item, "SET_DRINK", cmd["drink"]) if cmd.get("drink") else None
        if (cmd.get("side") and not side) or (cmd.get("drink") and not drink) or not set_opt:
            return None   # 없는 사이드·음료는 LLM이 손님에게 되묻는다

    if kind == "set_order":
        opts = [{"option_id": o["id"], "name": o["name_ko"]} for o in (set_opt, side, drink)]
        res = await api_client.add_cart_item(session_id, {
            "menu_item_id": item["id"], "quantity": cmd["qty"], "selected_options": opts, "special_note": None})
        cart_history.record_added(session_id, res.get("cart_item_id"), name, cmd["qty"])
        push_action({"type": "add_item", "menu_item_id": item["id"], "name": name, "quantity": cmd["qty"],
                     "upgrade_to_set": True, "side": side["name_ko"], "drink": drink["name_ko"],
                     "exclusions": [], "cart_item_id": res.get("cart_item_id")})
        return (f"{name} 세트 {cmd['qty']}개, 사이드 {side['name_ko']}, 음료 {drink['name_ko']} 담았습니다. "
                "다른 메뉴를 더 주문하시겠어요?")

    if kind == "to_set":
        lines = _lines_of(cart, item, is_set=False)
        if len(lines) != 1:
            return None
        opts = _keep_non_set(lines[0], item, set()) + [
            {"option_id": o["id"], "name": o["name_ko"]} for o in (set_opt, side, drink)]
        await api_client.patch_cart_item(session_id, lines[0]["cart_item_id"], {"selected_options": opts})
        push_action({"type": "update_item", "cart_item_id": lines[0]["cart_item_id"], "selected_options": opts})
        return f"{name}를 세트로 변경했습니다. 사이드는 {side['name_ko']}, 음료는 {drink['name_ko']}입니다."

    if kind == "to_single":
        lines = _lines_of(cart, item, is_set=True)
        if len(lines) != 1:
            return None
        opts = _keep_non_set(lines[0], item, set(_SET_NAMES))
        await api_client.patch_cart_item(session_id, lines[0]["cart_item_id"], {"selected_options": opts})
        push_action({"type": "update_item", "cart_item_id": lines[0]["cart_item_id"], "selected_options": opts})
        return f"{name}를 단품으로 변경했습니다."

    if kind == "set_options":
        lines = _lines_of(cart, item, is_set=True)
        if len(lines) != 1:
            return None
        drop = ({"SET_SIDE"} if side else set()) | ({"SET_DRINK"} if drink else set())
        opts = _keep_non_set(lines[0], item, drop) + [
            {"option_id": o["id"], "name": o["name_ko"]} for o in (side, drink) if o]
        await api_client.patch_cart_item(session_id, lines[0]["cart_item_id"], {"selected_options": opts})
        push_action({"type": "update_item", "cart_item_id": lines[0]["cart_item_id"], "selected_options": opts})
        got = ", ".join(x for x in (side and f"사이드 {side['name_ko']}", drink and f"음료 {drink['name_ko']}") if x)
        return f"{name} 세트의 {got}(으)로 변경했습니다."

    if kind == "remove_line":
        lines = _lines_of(cart, item, cmd["is_set"])
        if not lines or not _same_options(lines):
            return None   # 옵션이 다른 줄이 여럿이면(단품·세트 등) 어느 것인지 LLM이 되묻는다
        for line in lines:
            cart_history.record_removed(session_id, line)
            await api_client.remove_cart_item(session_id, line["cart_item_id"])
            push_action({"type": "remove_item", "cart_item_id": line["cart_item_id"]})
        return f"{name} 항목을 장바구니에서 삭제했습니다. 다른 메뉴를 더 주문하시겠어요?"

    if kind == "reduce_one":
        lines = _lines_of(cart, item, cmd["is_set"])
        total = sum(int(l.get("quantity", 1)) for l in lines)
        if not lines or total < 2 or not _same_options(lines):
            return None   # 1개뿐이면 "하나만 빼줘"는 삭제라서 LLM·삭제 가드가 이어받는다
        await _reduce_total(session_id, lines, 1)
        return f"{name} 1개를 줄여 {total - 1}개로 수정했습니다. 다른 메뉴를 더 주문하시겠어요?"

    if kind == "keep_n":
        lines = _lines_of(cart, item, cmd["is_set"])
        total = sum(int(l.get("quantity", 1)) for l in lines)
        if not lines or total <= cmd["n"] or not _same_options(lines):
            return None
        await _reduce_total(session_id, lines, total - cmd["n"])
        return f"{name}를 {cmd['n']}개만 남기고 정리했습니다. 다른 메뉴를 더 주문하시겠어요?"
    return None


async def try_command(session_id: str, text: str) -> str | None:
    """직접 처리할 수 있는 명령이면 처리하고 손님에게 할 말을, 아니면 None을 돌려준다. 실패해도 예외를 내지 않는다."""
    try:
        menu = await api_client.fetch_menu_items()
        cmd = parse_command(text, menu)
        if not cmd:
            return None
        reply = await execute(session_id, cmd, menu)
    except Exception:  # noqa: BLE001 - 직접 처리가 실패하면 LLM이 평소대로 처리한다
        return None
    if reply:
        record_guard("direct_command", f"「{text[:40]}」 {cmd['kind']}를 코드가 처리", blocked=False, fixed=True)
    return reply


def _spoken_option(item: dict, group: str, text: str) -> str | None:
    """텍스트에서 그 그룹의 옵션 이름이 하나로 정해지게 언급됐으면 그 이름. 없거나 여럿이면 None
    ("감자튀김"은 "양념감자튀김"에 들어 있으므로 더 긴 이름에 겹치는 것은 뺀다)."""
    compact = _compact(text)
    hits = []
    for o in item.get("options") or []:
        if o.get("option_group") != group or not o.get("is_available", True):
            continue
        key = _compact(o["name_ko"])
        if len(key) >= 2 and (key in compact or (len(key) >= 5 and key[:-1] in compact)):
            hits.append(o["name_ko"])
    hits = [h for h in hits if not any(h != x and _compact(h) in _compact(x) for x in hits)]
    return hits[0] if len(hits) == 1 else None


def parse_set_followup(user: str, recent: str, menu: list[dict]) -> dict | None:
    """"버거 세트로 하나 줘" → "사이드는 A" → "음료는 B"처럼 여러 턴에 걸친 세트 주문에서, 이번 발화로 사이드·음료가
    모두 정해졌을 때 담을 명령. 가장 최근에 버거 이름이 나온 발화가 세트 주문이어야 하고, 이번 발화가 사이드나 음료 이름을
    말해야 한다. (호출한 쪽이 직전 안내가 사이드·음료를 묻는 중인지 확인한다)"""
    if not guards.has_hangul(user) or guards.has_remove_intent(user) or guards.mentions_single(user):
        return None
    burgers = [i for i in menu if _is_burger(i)]
    pool: list[str] = []
    burger, qty = None, 1
    for turn in reversed([t for t in (recent or "").split("¦") if t.strip()]):
        pool.insert(0, turn)
        found = _one_named(turn, burgers)
        if found:
            if not guards.mentions_set(turn):
                return None
            burger, qty = found, guards.quantity_in(turn) or 1
            break
    if not burger:
        return None
    item = next((i for i in menu if i["id"] == burger["id"]), burger)
    if not (_spoken_option(item, "SET_SIDE", user) or _spoken_option(item, "SET_DRINK", user)):
        return None   # 이번 발화가 사이드·음료 이야기가 아니다
    text = " ".join(pool + [user])
    side, drink = _spoken_option(item, "SET_SIDE", text), _spoken_option(item, "SET_DRINK", text)
    if not (side and drink):
        return None
    return {"kind": "set_order", "item": burger, "qty": qty, "side": side, "drink": drink}


async def complete_set_followup(session_id: str, user: str, recent: str) -> str | None:
    """parse_set_followup이 정한 세트를 담고 손님에게 할 말을 돌려준다. 못 하면 None."""
    try:
        menu = await api_client.fetch_menu_items()
        cmd = parse_set_followup(user, recent, menu)
        reply = await execute(session_id, cmd, menu) if cmd else None
    except Exception:  # noqa: BLE001
        return None
    if reply:
        record_guard("set_followup_completed", f"「{user[:40]}」 여러 턴에 걸친 세트 주문을 코드가 담음", blocked=False, fixed=True)
    return reply
