#!/usr/bin/env python3
"""전체 흐름 시나리오 생성기 — 도입부 + 메뉴 선택·변경 n번 + 결제 블록을 섞어 만든다(테스트 용도).

손으로 쓰면 기대 장바구니가 틀리기 쉬워서, 참조 장바구니(RefCart)에 각 조작을 적용해 매 턴의 기대값을
자동으로 계산한다. 같은 시드는 항상 같은 시나리오를 만든다.

사용법 (backend 폴더에서, 백엔드가 떠 있어야 메뉴를 읽을 수 있다)
    python tools/flow_scenarios_gen.py --build-fixed                 # 고정 100개를 flow_scenarios_fixed.json으로 저장
    python tools/flow_scenarios_gen.py --preview 5 --seed 3          # 랜덤 5개를 LLM 없이 출력
    python tools/voice_scenario_suite.py --random 10 --seed 7        # 랜덤 10개를 만들어 실행
    python tools/voice_scenario_suite.py --category 대량흐름          # 고정 100개 실행
    python tools/voice_scenario_suite.py --category 대량흐름 --dry-run # 발화와 기대 장바구니만 출력(비용 0)
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import re
import sys
from pathlib import Path

import httpx

# ── 말투 도우미 ──────────────────────────────────────────────────────────────
_NUM = {1: "하나", 2: "두 개", 3: "세 개", 4: "네 개", 5: "다섯 개"}
_NUM_CUP = {1: "한 잔", 2: "두 잔", 3: "세 잔", 4: "네 잔", 5: "다섯 잔"}
_DIGIT_KO = {"0": "공", "1": "일", "2": "이", "3": "삼", "4": "사", "5": "오", "6": "육", "7": "칠", "8": "팔", "9": "구"}


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _spoken(menu_name: str) -> str:
    """메뉴 표기를 손님이 말하는 형태로: 괄호·공백 제거 ("콜라(M)" → "콜라", "F 버거" → "F버거")."""
    return _compact(re.sub(r"\(.*?\)", "", menu_name))


def _spoken_excl(opt_name: str) -> str:
    """"다진 양파 제외" → "양파", "채썬 양배추 제외" → "양배추"."""
    s = opt_name.replace("제외", "").replace("다진", "").replace("채썬", "")
    return _compact(s)


def _phone_text(rng: random.Random) -> tuple[str, str]:
    digits = "010" + "".join(rng.choice("0123456789") for _ in range(8))
    if rng.random() < 0.5:
        return digits, digits
    ko = " ".join("".join(_DIGIT_KO[c] for c in part) for part in (digits[:3], digits[3:7], digits[7:]))
    return digits, ko


# ── 메뉴 ─────────────────────────────────────────────────────────────────────
class MenuData:
    """/api/menu 응답에서 생성에 필요한 것만 뽑아 둔다."""

    def __init__(self, data: dict):
        items = data["menu_items"]
        self.burgers = []
        for b in items.get("burger", []):
            opts = b.get("options", [])
            if not any(o["option_group"] == "SET_UPGRADE" for o in opts):
                continue
            self.burgers.append({
                "name": b["name_ko"],
                "sides": [o["name_ko"] for o in opts if o["option_group"] == "SET_SIDE"],
                "drinks": [o["name_ko"] for o in opts if o["option_group"] == "SET_DRINK"],
                # 괄호가 들어 있는 재료("양배추(또는 양상추)")는 말하기 모호해서 제외
                "excls": [o["name_ko"] for o in opts if o["option_group"] == "EXCLUDE" and "(" not in o["name_ko"]],
            })
        # 단품 사이드·음료 풀: 서로의 부분 문자열이 되는 이름(감자튀김 ⊂ 양념감자튀김, 콜라 ⊂ 제로콜라)은
        # 기본 풀에서 빼고 어려운 풀(hard)에만 넣는다
        self.sides = [s["name_ko"] for s in items.get("side", [])]
        self.drinks = [d["name_ko"] for d in items.get("beverage", [])]

    def side_pool(self, hard: bool) -> list[str]:
        names = list(self.sides)
        if hard:
            return names
        return [n for n in names if not any(_spoken(n) != _spoken(m) and _spoken(n) in _spoken(m) for m in names)
                and not any(_spoken(m) != _spoken(n) and _spoken(m) in _spoken(n) for m in names)]

    def drink_pool(self, hard: bool) -> list[str]:
        names = list(self.drinks)
        if hard:
            return names
        return [n for n in names if not any(_spoken(n) != _spoken(m) and _spoken(n) in _spoken(m) for m in names)
                and not any(_spoken(m) != _spoken(n) and _spoken(m) in _spoken(n) for m in names)]

    def burger(self, name: str) -> dict:
        return next(b for b in self.burgers if b["name"] == name)


# ── 참조 장바구니 ────────────────────────────────────────────────────────────
class RefCart:
    """줄 = {name, kind(burger|side|drink), set, side, drink, excl[], qty}. 같은 구성은 하나로 합산한다."""

    def __init__(self):
        self.lines: list[dict] = []
        self.history: list[list[dict]] = []      # 담기 계열 조작 직전 스냅샷(되돌리기용)
        self.last_removed: dict | None = None

    @staticmethod
    def _key(l: dict):
        return (l["name"], l["set"], l.get("side"), l.get("drink"), tuple(sorted(l.get("excl", []))))

    def snapshot(self):
        self.history.append(copy.deepcopy(self.lines))

    def add(self, line: dict):
        for l in self.lines:
            if self._key(l) == self._key(line):
                l["qty"] += line["qty"]
                return
        self.lines.append(copy.deepcopy(line))

    def find(self, name: str, set_: bool | None = None) -> list[dict]:
        return [l for l in self.lines if l["name"] == name and (set_ is None or l["set"] == set_)]

    def unique(self, name: str, set_: bool | None = None) -> dict | None:
        found = self.find(name, set_)
        return found[0] if len(found) == 1 else None

    def expected(self) -> list[dict]:
        out = []
        for l in self.lines:
            opts = []
            if l["set"]:
                opts += ["세트 업그레이드", l["side"], l["drink"]]
            opts += list(l.get("excl", []))
            out.append({"name": l["name"], "opts": opts, "qty": l["qty"]})
        return out


def _burger_line(name, qty=1, set_=False, side=None, drink=None, excl=()):
    return {"name": name, "kind": "burger", "set": set_, "side": side, "drink": drink, "excl": list(excl), "qty": qty}


def _plain_line(name, kind, qty=1):
    return {"name": name, "kind": kind, "set": False, "side": None, "drink": None, "excl": [], "qty": qty}


# ── 생성 문맥 ────────────────────────────────────────────────────────────────
class Ctx:
    def __init__(self, rng: random.Random, menu: MenuData, hard: bool):
        self.rng, self.menu, self.hard = rng, menu, hard
        self.cart = RefCart()
        self.steps: list[dict] = []
        self.ops: list[str] = []
        # 한 시나리오에서 쓰는 후보를 미리 좁힌다: 이름이 서로 포함되는 버거(치즈 ⊂ 더블 치즈)는 함께 쓰지 않는다
        names = [b["name"] for b in menu.burgers]
        rng.shuffle(names)
        chosen: list[str] = []
        for n in names:
            if all(_compact(n) not in _compact(c) and _compact(c) not in _compact(n) for c in chosen):
                chosen.append(n)
            if len(chosen) == 4:
                break
        self.burgers = chosen
        self.sides = rng.sample(menu.side_pool(hard), k=min(3, len(menu.side_pool(hard))))
        self.drinks = rng.sample(menu.drink_pool(hard), k=min(3, len(menu.drink_pool(hard))))

    # 스텝 기록 -------------------------------------------------------------
    def say(self, text, op, lang="ko", **checks):
        self.steps.append({"kind": "say", "text": text, "lang": lang, "checks": checks, "op": op})

    def say_cart(self, text, op, **checks):
        """발화 한 턴 + 이 턴 뒤 장바구니가 참조 장바구니와 정확히 같아야 한다."""
        self.say(text, op, cart_exact=self.cart.expected(), **checks)

    def say_unchanged(self, text, op):
        self.say(text, op, cart_exact=self.cart.expected(), no_actions=["add_item"])

    def rec(self, kind, spec):
        self.steps.append({"kind": kind, **spec})

    # 이름 -------------------------------------------------------------------
    def label(self, line: dict, with_type: bool | None = None) -> str:
        """장바구니 줄을 말하는 표현. 버거는 단품/세트를 붙여 모호함을 줄인다."""
        if line["kind"] == "burger":
            t = "세트" if line["set"] else "단품"
            if with_type is None:
                with_type = True
            return f"{_spoken(line['name'])} {t}" if with_type else _spoken(line["name"])
        return _spoken(line["name"])

    def pick_burger(self):
        return self.rng.choice(self.burgers)

    def pick_side_item(self):
        return self.rng.choice(self.sides)

    def pick_drink_item(self):
        return self.rng.choice(self.drinks)

    def qty_word(self, n, drink=False):
        return (_NUM_CUP if drink else _NUM)[n]


# ── 조작(Op) ─────────────────────────────────────────────────────────────────
# 각 조작은 (가능 여부 함수, 실행 함수). 실행 함수는 ctx에 스텝을 기록하고 ctx.cart를 갱신한다.

def op_add_single(c: Ctx):
    b, n = c.pick_burger(), c.rng.randint(1, 3)
    c.cart.snapshot()
    c.cart.add(_burger_line(b, n))
    sp = _spoken(b)
    c.say_cart(c.rng.choice([f"{sp} 단품 {_NUM[n]} 주세요", f"{sp} 단품으로 {_NUM[n]} 줘", f"{sp} 단품 {_NUM[n]} 담아줘"]), "add_single")


def op_add_multi(c: Ctx):
    c.cart.snapshot()
    parts = []
    kinds = c.rng.sample(["burger", "side", "drink"], k=c.rng.choice([2, 3]))
    for k in kinds:
        n = c.rng.randint(1, 3)
        if k == "burger":
            b = c.pick_burger()
            c.cart.add(_burger_line(b, n))
            parts.append(f"{_spoken(b)} 단품 {_NUM[n]}")
        elif k == "side":
            s = c.pick_side_item()
            c.cart.add(_plain_line(s, "side", n))
            parts.append(f"{_spoken(s)} {_NUM[n]}")
        else:
            d = c.pick_drink_item()
            c.cart.add(_plain_line(d, "drink", n))
            parts.append(f"{_spoken(d)} {_NUM_CUP[n]}")
    c.say_cart(" 그리고 ".join(parts) + c.rng.choice([" 줘", " 주세요", " 담아줘"]), "add_multi")


def op_add_set_oneshot(c: Ctx):
    b = c.pick_burger()
    info = c.menu.burger(b)
    side, drink = c.rng.choice(info["sides"]), c.rng.choice(info["drinks"])
    n = c.rng.randint(1, 2)
    c.cart.snapshot()
    c.cart.add(_burger_line(b, n, True, side, drink))
    c.say_cart(f"{_spoken(b)} 세트 {_NUM[n]}, 사이드는 {_spoken(side)} 음료는 {_spoken(drink)}로 줘", "add_set_oneshot")


def op_add_set_ask(c: Ctx):
    b = c.pick_burger()
    info = c.menu.burger(b)
    side, drink = c.rng.choice(info["sides"]), c.rng.choice(info["drinks"])
    c.say_unchanged(f"{_spoken(b)} 세트로 하나 줘", "add_set_ask")
    c.say_unchanged(f"사이드는 {_spoken(side)}", "add_set_ask")
    c.cart.snapshot()
    c.cart.add(_burger_line(b, 1, True, side, drink))
    c.say_cart(c.rng.choice([f"음료는 {_spoken(drink)}", f"{_spoken(drink)}로 주세요"]), "add_set_ask")


def op_add_burger_ask(c: Ctx):
    b = c.pick_burger()
    c.say_unchanged(f"{_spoken(b)} 하나 줘", "add_burger_ask")
    c.cart.snapshot()
    c.cart.add(_burger_line(b, 1))
    c.say_cart("단품으로 줘", "add_burger_ask")


def _lines(c: Ctx, pred=lambda l: True):
    """이름+종류(단품/세트)로 유일하게 가리킬 수 있는 줄만 후보로 본다."""
    out = []
    for l in c.cart.lines:
        if not pred(l):
            continue
        if l["kind"] == "burger":
            if c.cart.unique(l["name"], l["set"]) is l:
                out.append(l)
        elif c.cart.unique(l["name"]) is l:
            out.append(l)
    return out


def op_remove_line(c: Ctx):
    l = c.rng.choice(_lines(c))
    label = c.label(l)
    all_word = " 전부" if l["qty"] > 1 else ""
    c.cart.last_removed = copy.deepcopy(l)
    c.cart.lines.remove(l)
    c.say_cart(c.rng.choice([f"{label}{all_word} 빼줘", f"{label}{all_word} 취소해줘", f"{label}{all_word} 지워줘"]), "remove_line")


def op_reduce_qty(c: Ctx):
    l = c.rng.choice(_lines(c, lambda x: x["qty"] >= 2))
    label = c.label(l)
    l["qty"] -= 1
    c.say_cart(c.rng.choice([f"{label} 하나만 빼줘", f"{label} 한 개 줄여줘"]), "reduce_qty")


def op_set_qty(c: Ctx):
    l = c.rng.choice(_lines(c))
    new = c.rng.choice([n for n in range(1, 6) if n != l["qty"]])
    label = c.label(l)
    l["qty"] = new
    c.say_cart(f"{label} {new}개로 바꿔줘", "set_qty")


def op_add_more(c: Ctx):
    l = c.rng.choice(_lines(c))
    n = c.rng.randint(1, 2)
    c.cart.snapshot()
    l["qty"] += n
    label = c.label(l)
    c.say_cart(f"{label} {_NUM[n]} 더 줘", "add_more")


def op_undo_last(c: Ctx):
    c.lines_backup = None
    c.cart.lines = c.cart.history.pop()
    c.say_cart("방금 담은 거 취소해줘", "undo_last")


def op_readd_removed(c: Ctx):
    l = c.cart.last_removed
    c.cart.snapshot()
    c.cart.add(l)
    c.cart.last_removed = None
    if l["kind"] == "burger" and l["set"]:
        text = f"아까 뺀 {_spoken(l['name'])} 세트 같은 구성으로 다시 담아줘"
    elif l["kind"] == "burger":
        text = f"아까 뺀 {_spoken(l['name'])} 단품 다시 담아줘"
    else:
        text = f"아까 뺀 {_spoken(l['name'])} 다시 담아줘"
    c.say_cart(text, "readd_removed")


def op_change_side(c: Ctx):
    l = c.rng.choice(_lines(c, lambda x: x["set"] and x["qty"] == 1))
    info = c.menu.burger(l["name"])
    new = c.rng.choice([s for s in info["sides"] if s != l["side"]])
    l["side"] = new
    c.say_cart(f"{_spoken(l['name'])} 세트 사이드를 {_spoken(new)}로 바꿔줘", "change_side")


def op_change_drink(c: Ctx):
    l = c.rng.choice(_lines(c, lambda x: x["set"] and x["qty"] == 1))
    info = c.menu.burger(l["name"])
    new = c.rng.choice([d for d in info["drinks"] if d != l["drink"]])
    l["drink"] = new
    c.say_cart(f"{_spoken(l['name'])} 세트 음료를 {_spoken(new)}로 바꿔줘", "change_drink")


def op_change_both(c: Ctx):
    l = c.rng.choice(_lines(c, lambda x: x["set"] and x["qty"] == 1))
    info = c.menu.burger(l["name"])
    s2 = c.rng.choice([s for s in info["sides"] if s != l["side"]])
    d2 = c.rng.choice([d for d in info["drinks"] if d != l["drink"]])
    l["side"], l["drink"] = s2, d2
    c.say_cart(f"{_spoken(l['name'])} 세트 사이드는 {_spoken(s2)} 음료는 {_spoken(d2)}로 바꿔줘", "change_both")


def op_convert_to_set(c: Ctx):
    l = c.rng.choice(_lines(c, lambda x: x["kind"] == "burger" and not x["set"] and x["qty"] == 1))
    info = c.menu.burger(l["name"])
    side, drink = c.rng.choice(info["sides"]), c.rng.choice(info["drinks"])
    # 같은 이름의 세트 줄이 이미 있으면 합산 규칙이 모호해지므로 가능 조건에서 걸러 두었다
    l["set"], l["side"], l["drink"] = True, side, drink
    c.say_cart(f"{_spoken(l['name'])} 단품을 세트로 바꿔줘. 사이드는 {_spoken(side)} 음료는 {_spoken(drink)}", "convert_to_set")


def op_convert_to_single(c: Ctx):
    l = c.rng.choice(_lines(c, lambda x: x["kind"] == "burger" and x["set"] and x["qty"] == 1))
    l["set"], l["side"], l["drink"] = False, None, None
    c.say_cart(f"{_spoken(l['name'])} 세트 말고 단품으로 바꿔줘", "convert_to_single")


def op_add_exclusion(c: Ctx):
    cands = [l for l in _lines(c, lambda x: x["kind"] == "burger" and x["qty"] == 1)
             if [e for e in c.menu.burger(l["name"])["excls"] if e not in l["excl"]]]
    l = c.rng.choice(cands)
    opt = c.rng.choice([e for e in c.menu.burger(l["name"])["excls"] if e not in l["excl"]])
    l["excl"].append(opt)
    c.say_cart(f"{c.label(l)} {_spoken_excl(opt)} 빼주세요", "add_exclusion")


def op_remove_exclusion(c: Ctx):
    l = c.rng.choice(_lines(c, lambda x: x["kind"] == "burger" and x["qty"] == 1 and x["excl"]))
    opt = c.rng.choice(l["excl"])
    l["excl"].remove(opt)
    c.say_cart(f"{c.label(l)} {_spoken_excl(opt)} 다시 넣어줘", "remove_exclusion")


def op_add_second_set(c: Ctx):
    base = c.rng.choice(_lines(c, lambda x: x["kind"] == "burger" and x["set"] and x["qty"] == 1))
    info = c.menu.burger(base["name"])
    s2 = c.rng.choice([s for s in info["sides"] if s != base["side"]])
    d2 = c.rng.choice([d for d in info["drinks"] if d != base["drink"]])
    c.cart.snapshot()
    c.cart.add(_burger_line(base["name"], 1, True, s2, d2))
    c.say_cart(f"{_spoken(base['name'])} 세트 하나 더, 이번엔 사이드는 {_spoken(s2)} 음료는 {_spoken(d2)}로 줘", "add_second_set")


def op_query(c: Ctx):
    text = c.rng.choice(["지금 뭐 담겼어?", "장바구니에 뭐 있는지 알려줘", "가장 저렴한 버거가 뭐예요?"])
    c.say_unchanged(text, "query")


def op_touch_add(c: Ctx):
    b, n = c.pick_burger(), c.rng.randint(1, 2)
    c.cart.snapshot()
    c.cart.add(_burger_line(b, n))
    c.rec("touch_add", {"name": b, "qty": n, "set": False, "side": None, "drink": None, "exclude": None, "op": "touch_add"})


def op_touch_remove(c: Ctx):
    # 터치 삭제는 이름으로 줄을 찾으므로, 같은 이름의 다른 구성(단품/세트)이 없는 줄만 고른다
    l = c.rng.choice(_lines(c, lambda x: len(c.cart.find(x["name"])) == 1))
    c.cart.lines.remove(l)
    c.rec("touch_remove", {"name": l["name"], "op": "touch_remove"})


# 가능 여부(현재 장바구니 상태에서 이 조작이 말이 되는가)
def _has(c, pred):
    return bool(_lines(c, pred))


OPS = {
    "add_single":       (lambda c: True, op_add_single),
    "add_multi":        (lambda c: True, op_add_multi),
    "add_set_oneshot":  (lambda c: True, op_add_set_oneshot),
    "add_set_ask":      (lambda c: True, op_add_set_ask),
    "add_burger_ask":   (lambda c: True, op_add_burger_ask),
    "remove_line":      (lambda c: bool(_lines(c)), op_remove_line),
    "reduce_qty":       (lambda c: _has(c, lambda x: x["qty"] >= 2), op_reduce_qty),
    "set_qty":          (lambda c: bool(_lines(c)), op_set_qty),
    "add_more":         (lambda c: bool(_lines(c)), op_add_more),
    "undo_last":        (lambda c: bool(c.cart.history) and c.last_op in _UNDOABLE, op_undo_last),
    "readd_removed":    (lambda c: c.cart.last_removed is not None and c.last_op == "remove_line", op_readd_removed),
    "change_side":      (lambda c: _has(c, lambda x: x["set"] and x["qty"] == 1), op_change_side),
    "change_drink":     (lambda c: _has(c, lambda x: x["set"] and x["qty"] == 1), op_change_drink),
    "change_both":      (lambda c: _has(c, lambda x: x["set"] and x["qty"] == 1), op_change_both),
    "convert_to_set":   (lambda c: _has(c, lambda x: x["kind"] == "burger" and not x["set"] and x["qty"] == 1
                                        and not c.cart.find(x["name"], True)), op_convert_to_set),
    "convert_to_single": (lambda c: _has(c, lambda x: x["kind"] == "burger" and x["set"] and x["qty"] == 1
                                         and not c.cart.find(x["name"], False)), op_convert_to_single),
    "add_exclusion":    (lambda c: any([e for e in c.menu.burger(l["name"])["excls"] if e not in l["excl"]]
                                       for l in _lines(c, lambda x: x["kind"] == "burger" and x["qty"] == 1)), op_add_exclusion),
    "remove_exclusion": (lambda c: _has(c, lambda x: x["kind"] == "burger" and x["qty"] == 1 and x["excl"]), op_remove_exclusion),
    "add_second_set":   (lambda c: _has(c, lambda x: x["kind"] == "burger" and x["set"] and x["qty"] == 1), op_add_second_set),
    "query":            (lambda c: bool(c.cart.lines), op_query),
    "touch_add":        (lambda c: True, op_touch_add),
    "touch_remove":     (lambda c: len(c.cart.lines) >= 2 and _has(c, lambda x: len(c.cart.find(x["name"])) == 1), op_touch_remove),
}
_UNDOABLE = {"add_single", "add_burger_ask", "add_set_oneshot", "add_set_ask", "add_more", "add_multi",
             "add_second_set", "touch_add"}
# "방금 거 취소"는 한 번에 한 줄만 담긴 직전 조작에서만 쓴다(여러 줄을 담은 add_multi는 되돌릴 대상이 모호)
_UNDOABLE -= {"add_multi", "touch_add"}

TIERS = {
    "기본 다품목": (["add_single", "add_multi", "add_burger_ask", "set_qty", "add_more", "query"], (2, 4), False),
    "편집": (["add_single", "add_multi", "add_burger_ask", "remove_line", "reduce_qty", "undo_last",
              "readd_removed", "add_more", "set_qty", "query"], (4, 7), False),
    "세트 옵션": (["add_set_oneshot", "add_set_ask", "add_single", "change_side", "change_drink", "change_both",
                 "convert_to_set", "convert_to_single", "add_exclusion", "remove_exclusion", "add_second_set"], (3, 6), False),
    "종합": (list(OPS), (5, 8), True),
}
# 편집·세트 옵션 조작이 반드시 들어가도록 가중치를 주는 조작
_MUST = {
    "편집": ["remove_line", "undo_last", "reduce_qty", "readd_removed"],
    "세트 옵션": ["change_side", "change_drink", "change_both", "convert_to_set", "convert_to_single", "add_exclusion", "add_second_set"],
    "종합": ["remove_line", "undo_last", "change_side", "convert_to_set", "convert_to_single", "touch_add"],
}


# ── 도입부 · 결제 블록 ───────────────────────────────────────────────────────
def intro(c: Ctx) -> str:
    kind = c.rng.choice(["greet_dine", "greet_take", "direct_take", "orderType_screen", "menu_first",
                         "english", "touch_type", "stt_naejang"])
    if kind == "greet_dine":
        c.rec("state", {"screen": "start", "order_type": None})
        c.say("안녕하세요", "intro", no_actions=["add_item"], out_any=["매장", "포장"])
        c.say("매장에서 먹을게요", "intro", actions=["order_type"])
    elif kind == "greet_take":
        c.rec("state", {"screen": "start", "order_type": None})
        c.say("안녕하세요", "intro", no_actions=["add_item"], out_any=["매장", "포장"])
        c.say("포장할게요", "intro", actions=["order_type"])
    elif kind == "direct_take":
        c.rec("state", {"screen": "start", "order_type": None})
        c.say("포장해 갈게요", "intro", actions=["order_type"])
    elif kind == "orderType_screen":
        c.rec("state", {"screen": "orderType", "order_type": None})
        c.say("여기서 먹고 갈게요", "intro", actions=["order_type"])
    elif kind == "menu_first":
        c.rec("state", {"screen": "start", "order_type": None})
        c.say("안녕하세요", "intro", no_actions=["add_item"], out_any=["매장", "포장"])
        c.say("매장에서 먹을게요", "intro", actions=["order_type"])
        c.say("버거 뭐 있어요?", "intro", no_actions=["add_item"])
    elif kind == "english":
        c.rec("state", {"screen": "start", "order_type": None})
        c.say("Hello", "intro", lang="en", reply_lang="en", no_actions=["add_item"])
        c.say("Dine in please", "intro", lang="en", actions=["order_type"])
    elif kind == "touch_type":
        c.rec("state", {"screen": "menu", "order_type": c.rng.choice(["dine-in", "takeout"])})
    else:  # STT가 "매장"을 "내장"으로 받아 적은 경우(서버가 교정한다)
        c.rec("state", {"screen": "start", "order_type": None})
        c.say("안녕하세요", "intro", no_actions=["add_item"], out_any=["매장", "포장"])
        c.say("내장에서 먹을게.", "intro", actions=["order_type"])
    return kind


def _method(c: Ctx) -> str:
    return c.rng.choice(["카드로 할게요", "현금으로 낼게요", "카카오페이로 할게요", "삼성페이로 할게요", "간편결제로 할게요"])


def payment(c: Ctx) -> str:
    kind = c.rng.choice(["no_points", "no_points", "points_phone", "points_inline", "method_change", "back_to_menu"])
    c.say("결제할게요", "pay_start", cart_exact=c.cart.expected(), actions=["start_checkout"])
    if kind == "no_points":
        c.say("적립 안 할게요", "pay_points", actions=["points"])
        c.say(_method(c), "pay_method", actions=["payment_method"])
    elif kind == "points_phone":
        digits, spoken = _phone_text(c.rng)
        c.say("포인트 적립할게요", "pay_points", actions=["points"])
        c.say(spoken, "pay_phone", actions=["points_phone"])
        c.say(_method(c), "pay_method", actions=["payment_method"])
    elif kind == "points_inline":
        digits, spoken = _phone_text(c.rng)
        c.say(f"네 적립할게요 {digits}", "pay_phone", actions=["points_phone"])
        c.say(_method(c), "pay_method", actions=["payment_method"])
    elif kind == "method_change":
        c.say("적립 안 할게요", "pay_points", actions=["points"])
        c.say("현금으로 낼게요", "pay_method", actions=["payment_method"])
        c.say("아 카드로 바꿀게요", "pay_method_change", actions=["payment_method"])
    else:  # 결제 도중 메뉴를 추가하러 돌아감
        d = c.pick_drink_item()
        c.cart.add(_plain_line(d, "drink", 1))
        c.say_cart(f"아 잠깐 {_spoken(d)}도 한 잔 추가할게요", "pay_back_add")
        c.say("이제 결제할게요", "pay_start", out_any=["포인트", "적립"])
        c.say("적립 안 할게요", "pay_points", actions=["points"])
        c.say(_method(c), "pay_method", actions=["payment_method"])
    return kind


# ── 시나리오 조립 ────────────────────────────────────────────────────────────
def build_one(rng: random.Random, menu: MenuData, tier: str, sid: str, category: str):
    ops_list, (lo, hi), hard = TIERS[tier]
    c = Ctx(rng, menu, hard)
    c.last_op = None
    intro_kind = intro(c)
    n = rng.randint(lo, hi)
    must = list(_MUST.get(tier, []))
    rng.shuffle(must)
    for i in range(n):
        feasible = [name for name in ops_list if OPS[name][0](c)]
        # 첫 조작은 담기여야 한다
        if not c.cart.lines:
            feasible = [x for x in feasible if x.startswith("add") or x == "touch_add"] or ["add_single"]
        pref = [m for m in must if m in feasible]
        # 남은 칸 수가 필수 조작 수와 같거나 적으면 필수 조작을 우선 고른다
        name = pref[0] if pref and (n - i) <= len(must) + 1 else rng.choice(feasible)
        if name in must:
            must.remove(name)
        OPS[name][1](c)
        c.ops.append(name)
        c.last_op = name
        # 장바구니가 비면 다음 조작에서 담기부터 하도록 자연스럽게 흘러간다
    if not c.cart.lines:
        op_add_single(c)
        c.ops.append("add_single")
    pay_kind = payment(c)
    title = f"[{tier}] {intro_kind} · {'>'.join(c.ops)} · {pay_kind}"
    # 순수 딕셔너리로 돌려준다(voice_scenario_suite의 Scenario로 바꾸는 일은 실행기가 한다 — 순환 임포트 방지)
    return {"id": sid, "category": category, "title": title, "steps": c.steps}


def fetch_menu(base: str) -> MenuData:
    return MenuData(httpx.get(f"{base}/api/menu", timeout=30).json())


FIXED_PATH = Path(__file__).with_name("flow_scenarios_fixed.json")
FIXED_COUNTS = [("기본 다품목", 25), ("편집", 30), ("세트 옵션", 25), ("종합", 20)]   # 합계 100
FIXED_SEED = 20261002


def generate_fixed(menu: MenuData):
    out, idx = [], 0
    for tier, count in FIXED_COUNTS:
        for _ in range(count):
            idx += 1
            rng = random.Random(f"{FIXED_SEED}-{idx}")
            out.append(build_one(rng, menu, tier, f"W{idx:03d}", "대량흐름"))
    return out


def generate_random(menu: MenuData, count: int, seed: int):
    out = []
    rng0 = random.Random(f"rand-{seed}")
    tiers = list(TIERS)
    for i in range(1, count + 1):
        tier = rng0.choice(tiers)
        rng = random.Random(f"{seed}-{i}")
        out.append(build_one(rng, menu, tier, f"R{seed}-{i:02d}", "랜덤흐름"))
    return out


def load_fixed() -> list[dict]:
    if not FIXED_PATH.exists():
        return []
    return json.loads(FIXED_PATH.read_text(encoding="utf-8"))


def describe(sc: dict) -> str:
    lines = [f"{sc['id']}  {sc['title']}"]
    for st in sc["steps"]:
        k = st["kind"]
        if k == "say":
            exp = st["checks"].get("cart_exact")
            tail = ""
            if exp is not None:
                tail = "   → " + ", ".join(f"{e['name']}{'(' + '/'.join(e['opts']) + ')' if e['opts'] else ''}×{e['qty']}" for e in exp) if exp else "   → (빈 장바구니)"
            lines.append(f"    말: {st['text']}{tail}")
        else:
            lines.append(f"    [{k}] " + ", ".join(f"{a}={b}" for a, b in st.items() if a not in ('kind', 'op')))
    return "\n".join(lines)


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8001")
    ap.add_argument("--build-fixed", action="store_true")
    ap.add_argument("--preview", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    menu = fetch_menu(a.url)
    if a.build_fixed:
        scs = generate_fixed(menu)
        FIXED_PATH.write_text(json.dumps(scs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(scs)}개 시나리오를 {FIXED_PATH} 에 저장")
    if a.preview:
        for s in generate_random(menu, a.preview, a.seed):
            print(describe(s), "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
