#!/usr/bin/env python3
"""LLM이 연기하는 손님으로 키오스크를 끝까지 주문해 보는 탐색용 시뮬레이터(층 C).

랜덤 흐름(flow_scenarios_gen)은 말이 정해진 템플릿이라 정답을 턴마다 계산할 수 있지만 사람 같은 변이는 작다.
여기서는 반대로, 페르소나와 "목표 주문"만 정해 주고 LLM 손님이 키오스크의 응답을 보며 자유롭게 말한다.
손님은 장바구니를 볼 수 없고 키오스크가 한 말만 듣는다. 정답은 턴마다가 아니라 끝에서 한 번만 본다:
    최종 서버 장바구니 == 목표 주문 이고, 결제 수단까지 도달했는가.
중간 문제는 이상 패턴(무응답, 같은 응답 반복, 손님이 같은 말을 반복)으로 잡는다.

비결정적이고 토큰이 든다 — 회귀 검사가 아니라 약점 탐색용이다. 실패한 대화는 --save-failed로 저장해
voice_scenario_suite의 고정 시나리오(층 A·B)로 옮겨 쓴다.

사용법 (backend 폴더에서, 백엔드가 떠 있어야 한다. OPENAI_API_KEY 필요)
    python tools/persona_sim.py --dry-run --count 4 --seed 3        # 목표와 손님 프롬프트만 출력(LLM·서버 호출 없음)
    python tools/persona_sim.py --count 6 --seed 3                  # 6명 실행
    python tools/persona_sim.py --persona 알레르기부모 급한직장인 --count 4 --save-failed failed_sim.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

END = "[END]"
MAX_TURNS = 18


# ── 페르소나 ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Persona:
    name: str
    style: str                 # LLM 손님에게 주는 말투·행동 지시
    lang: str = "ko"
    human: int = 0             # 손님 발화에 입히는 STT식 변형 강도(flow_scenarios_gen.humanize)
    allergy: bool = False      # 목표 주문을 알레르기에 맞춘다
    changes_mind: bool = False  # 처음 고른 버거를 중간에 다른 버거로 바꾼다
    sets: bool = True          # 세트를 주문하는가(False면 단품 위주)


PERSONAS: dict[str, Persona] = {p.name: p for p in [
    Persona("할머니", "80세 할머니. 천천히 존댓말로 말하고 메뉴 이름을 정확히 몰라 \"그 치즈 들어간 거\" 같이 돌려 말하다가, "
                    "키오스크가 이름을 알려 주면 그 이름으로 주문한다. 가끔 \"뭐라고요?\" 하고 되묻는다.", human=1, sets=False),
    Persona("급한직장인", "점심시간에 바쁜 직장인. 아주 짧은 반말로 말한다. 한 문장에 여러 메뉴를 몰아서 말한다. 키오스크가 길게 말하면 짜증을 낸다.", human=1),
    Persona("말많은손님", "수다스러운 손님. 주문 사이사이에 잡담(날씨, 오늘 있었던 일)을 섞고 \"음...\", \"어...\" 같은 군말이 많다. 그래도 주문은 끝낸다.", human=2),
    Persona("알레르기부모", "알레르기가 있는 아이의 부모. 주문 전에 아이의 알레르기를 밝히고, 그 성분이 든 메뉴는 주문하지 않는다. "
                       "키오스크 설명을 꼼꼼히 확인한다.", allergy=True),
    Persona("마음바꾸는손님", "결정을 잘 못 하는 손님. 처음 말한 버거를 바로 \"아 그거 말고\" 하며 다른 버거로 바꾼다. 최종 선택은 목표 주문이다.",
            human=1, changes_mind=True),
    Persona("외국인", "한국어를 못 하는 영어 사용자. 영어로만 말한다. 메뉴 이름은 영어로 설명하거나 읽을 수 있는 대로 말한다.", lang="en"),
    Persona("진상", "불평이 많고 말을 자주 끊는 손님. 가격이 비싸다고 투덜대고 반말을 쓰지만 결국 목표 주문대로 결제한다.", human=1),
]}


# ── 목표 주문 ────────────────────────────────────────────────────────────────
@dataclass
class Goal:
    lines: list[dict]                    # gen._burger_line / _plain_line 형식
    order_type: str                      # dine-in | takeout
    method: str                          # 카드 | 현금 | 간편결제
    first_pick: str | None = None        # 마음바꾸는손님: 처음 말할 (최종과 다른) 버거
    allergy_name: str | None = None      # 알레르기부모: 알레르기 성분 이름(DB 마스터의 name_ko)
    expected: list[dict] = field(default_factory=list)


def make_goal(menu, rng: random.Random, persona: Persona):
    """gen.MenuData로 목표 주문을 만든다. 정답 장바구니는 flow_scenarios_gen.RefCart가 계산한다."""
    from tools import flow_scenarios_gen as gen
    cart = gen.RefCart()
    names = [b["name"] for b in menu.burgers]
    rng.shuffle(names)
    allergy_name = None
    if persona.allergy:
        # 이 성분이 든 버거와 안 든 버거가 모두 있는 성분을 고른다
        cands = sorted({n for b in menu.burgers for n in b["allergens"].values()})
        rng.shuffle(cands)
        for n in cands:
            safe = [b["name"] for b in menu.burgers if n not in b["allergens"].values()]
            if safe and len(safe) < len(menu.burgers):
                allergy_name = n
                names = safe
                break
    picked: list[str] = []
    target = rng.randint(1, 2)
    for n in names:   # 이름이 서로 포함되는 버거(치즈 ⊂ 더블 치즈)는 한 주문에 함께 넣지 않는다
        if all(gen._compact(n) not in gen._compact(p) and gen._compact(p) not in gen._compact(n) for p in picked):
            picked.append(n)
        if len(picked) >= target:
            break
    for n in picked:
        info = menu.burger(n)
        qty = rng.choice([1, 1, 1, 2])
        if persona.sets and rng.random() < 0.7:
            side, drink = rng.choice(info["sides"]), rng.choice(info["drinks"])
            cart.add(gen._burger_line(n, qty, True, side, drink))
        else:
            excl = []
            if info["excls"] and rng.random() < 0.3:
                excl = [rng.choice(info["excls"])]
            cart.add(gen._burger_line(n, qty, False, excl=excl))
    if rng.random() < 0.4:
        drinks = menu.drink_pool(False)
        if drinks:
            cart.add(gen._plain_line(rng.choice(drinks), "drink", 1))
    first_pick = None
    if persona.changes_mind:
        others = [b["name"] for b in menu.burgers if b["name"] not in {l["name"] for l in cart.lines}]
        first_pick = rng.choice(others) if others else None
    return Goal(lines=cart.lines, order_type=rng.choice(["dine-in", "takeout"]), method=rng.choice(["카드", "현금", "간편결제"]),
                first_pick=first_pick, allergy_name=allergy_name, expected=cart.expected())


def describe_goal(goal: Goal, lang: str = "ko") -> str:
    parts = []
    for l in goal.lines:
        text = f"{l['name']} {'세트' if l['set'] else '단품'} {l['qty']}개" if l["kind"] == "burger" else f"{l['name']} {l['qty']}개"
        extra = []
        if l["set"]:
            extra += [f"사이드는 {l['side']}", f"음료는 {l['drink']}"]
        if l.get("excl"):
            extra.append(", ".join(l["excl"]) + " 빼고")
        parts.append(text + (f" ({', '.join(extra)})" if extra else ""))
    where = "매장에서 먹는다" if goal.order_type == "dine-in" else "포장한다"
    return f"{where}. 주문: " + " / ".join(parts) + f". 결제는 {goal.method}로, 포인트 적립은 하지 않는다."


def build_customer_prompt(persona: Persona, goal: Goal) -> str:
    lang_rule = "모든 말을 한국어 구어체로 한다." if persona.lang == "ko" else "Speak only in English, like a tourist. Never use Korean."
    extra = []
    if goal.allergy_name:
        extra.append(f"아이가 {goal.allergy_name} 알레르기가 있다. 주문 전에 이 사실을 말하고, 키오스크 안내가 맞는지 한 번 확인한다.")
    if goal.first_pick:
        extra.append(f"처음에는 {goal.first_pick}를 주문한다고 말했다가, 곧바로 \"아 그거 말고\" 하며 목표 주문의 버거로 바꾼다.")
    return (
        "너는 패스트푸드점 키오스크(음성 주문)를 쓰는 손님을 연기한다. 키오스크의 말만 듣고 대답한다(화면은 보지 못한다).\n"
        f"성격과 말투: {persona.style}\n"
        f"{lang_rule}\n"
        f"목표 주문(너만 아는 정보): {describe_goal(goal)}\n"
        + ("".join(f"{e}\n" for e in extra))
        + "규칙:\n"
        "- 한 번에 한두 문장만 말한다. 실제 사람이 말하듯 짧게.\n"
        "- 목표를 한꺼번에 읊지 말고, 키오스크가 묻는 순서대로 필요한 만큼만 말한다(성격상 몰아서 말하는 사람이면 그렇게).\n"
        "- 키오스크가 틀리게 담았거나 잘못 알아들었다고 느끼면 정정한다.\n"
        "- 목표 주문이 모두 담겼다고 느끼면 \"결제할게요\"라고 하고, 포인트 적립은 하지 않겠다고 하고, 결제 수단을 말한다.\n"
        f"- 결제 수단까지 말한 다음 턴에는 {END} 만 출력한다. 말이 막혀 더 진행할 수 없어도 {END} 만 출력한다.\n"
        "- 출력은 손님이 하는 말 한 줄뿐이다. 따옴표나 설명 없이."
    )


# ── 이상 패턴 ────────────────────────────────────────────────────────────────
def _n(s: str) -> str:
    return re.sub(r"[\s.,!?~…]+", "", s or "").lower()


def detect_anomalies(turns: list[dict]) -> list[str]:
    """turns: [{say, output, ms, ...}]. 응답이 비었거나, 같은 응답이 3번 연속이거나, 손님이 같은 말을 연달아 반복하면 기록한다."""
    out = []
    for i, t in enumerate(turns, 1):
        if not (t.get("output") or "").strip():
            out.append(f"T{i} 키오스크 응답이 비어 있음 (손님: 「{t['say'][:30]}」)")
        if t.get("ms", 0) > 15000:
            out.append(f"T{i} 응답 지연 {t['ms'] / 1000:.1f}초")
    for i in range(2, len(turns)):
        if turns[i]["output"] and _n(turns[i]["output"]) == _n(turns[i - 1]["output"]) == _n(turns[i - 2]["output"]):
            out.append(f"T{i + 1} 같은 응답 3회 연속: 「{turns[i]['output'][:30]}」")
    for i in range(1, len(turns)):
        if _n(turns[i]["say"]) and _n(turns[i]["say"]) == _n(turns[i - 1]["say"]):
            out.append(f"T{i + 1} 손님이 같은 말을 반복(알아듣지 못했다는 신호): 「{turns[i]['say'][:30]}」")
    return out


# ── 시뮬레이션 ───────────────────────────────────────────────────────────────
@dataclass
class SimResult:
    persona: str
    goal_text: str
    turns: list[dict] = field(default_factory=list)
    cart_ok: bool = False
    cart_msg: str | None = None
    paid: bool = False
    anomalies: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.cart_ok and self.paid


def simulate(persona: Persona, goal: Goal, customer, kiosk, humanize_rng: random.Random | None = None, max_turns: int = MAX_TURNS) -> SimResult:
    """customer(messages) -> 손님 한 줄 / kiosk.say(text) -> {output, actions, guards, ms} / kiosk.cart() -> 서버 장바구니.
    둘 다 주입식이라 LLM·서버 없이 테스트할 수 있다."""
    from tools import flow_scenarios_gen as gen
    from tools.voice_scenario_suite import cart_exact_fail
    res = SimResult(persona.name, describe_goal(goal))
    system = build_customer_prompt(persona, goal)
    history: list[dict] = [{"role": "user", "content": "(키오스크 화면이 켜져 있다. 손님으로서 첫마디를 한다.)"}]
    try:
        for _ in range(max_turns):
            say = (customer(system, history) or "").strip()
            if not say or say.startswith(END):
                break
            if humanize_rng is not None and persona.lang == "ko":
                say = gen.humanize(say, humanize_rng, persona.human)
            reply = kiosk.say(say)
            types = [a for a in reply["actions"]]
            res.turns.append({"say": say, "output": reply["output"], "actions": types, "ms": reply.get("ms", 0),
                              "guards": [g.get("rule") for g in reply.get("guards", [])]})
            history.append({"role": "assistant", "content": say})
            history.append({"role": "user", "content": f"키오스크: {reply['output'] or '(아무 말도 하지 않음)'}"})
            if "payment_method" in types:
                res.paid = True
                break
        res.anomalies = detect_anomalies(res.turns)
        res.cart_msg = cart_exact_fail(kiosk.cart(), goal.expected)
        res.cart_ok = res.cart_msg is None
    except Exception as e:  # noqa: BLE001
        res.error = f"{type(e).__name__}: {e}"
    return res


class HttpKiosk:
    """voice_scenario_suite.run_scenario와 같은 방식으로 /ai_modules/llm을 부른다(화면·주문 유형 상태는 액션을 보고 갱신)."""

    def __init__(self, base: str, lang: str):
        self.base, self.lang = base, lang
        self.sid = f"ps-{uuid.uuid4().hex[:8]}"
        self.screen, self.order_type = "start", None

    def say(self, text: str) -> dict:
        t0 = time.time()
        r = httpx.post(f"{self.base}/ai_modules/llm", timeout=120, json={
            "session_id": self.sid, "input": text, "language": self.lang, "screen": self.screen, "order_type": self.order_type})
        ms = int((time.time() - t0) * 1000)
        r.raise_for_status()
        data = r.json()
        actions = data.get("actions") or []
        for a in actions:
            if a.get("type") == "order_type":
                self.order_type = "takeout" if a.get("value") == "takeout" else "dine-in"
                self.screen = "menu"
            elif a.get("type") == "navigate":
                self.screen = a.get("screen", self.screen)
            elif a.get("type") in ("checkout", "start_checkout"):
                self.screen = "cart"
        return {"output": data.get("output") or "", "actions": [a.get("type") for a in actions], "guards": data.get("guards") or [], "ms": ms}

    def cart(self) -> list[dict]:
        from tools.voice_scenario_suite import cart_snapshot
        return cart_snapshot(self.base, self.sid)

    def close(self):
        try:
            httpx.delete(f"{self.base}/api/cart/{self.sid}", timeout=30)
            httpx.post(f"{self.base}/ai_modules/llm/reset", params={"session_id": self.sid}, timeout=30)
        except Exception:  # noqa: BLE001
            pass


def openai_customer(model: str, temperature: float, seed: int | None):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30, max_retries=1)

    def ask(system: str, history: list[dict]) -> str:
        kwargs = {"seed": seed} if seed is not None else {}
        r = client.chat.completions.create(model=model, temperature=temperature, max_tokens=120,
                                           messages=[{"role": "system", "content": system}, *history], **kwargs)
        return r.choices[0].message.content or ""
    return ask


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8001")
    ap.add_argument("--persona", nargs="*", choices=list(PERSONAS), help="쓸 페르소나(기본: 전부 돌아가며)")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1, help="목표 주문과 손님 LLM 시드(LLM은 같은 시드여도 완전히 같지 않을 수 있다)")
    ap.add_argument("--model", default=None, help="손님 LLM(기본: PERSONA_SIM_MODEL 또는 OPENAI_LLM_MODEL 또는 gpt-4o-mini)")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--dry-run", action="store_true", help="목표와 손님 프롬프트만 출력(LLM·서버 호출 없음; 메뉴 조회에는 서버 필요)")
    ap.add_argument("--save-failed", default=None, help="실패한 대화를 이 JSON 파일에 저장")
    ap.add_argument("--json", default=None, help="모든 대화를 이 JSON 파일에 저장")
    a = ap.parse_args()

    from tools import flow_scenarios_gen as gen
    menu = gen.fetch_menu(a.url)
    names = a.persona or list(PERSONAS)
    plan = []
    for i in range(a.count):
        persona = PERSONAS[names[i % len(names)]]
        rng = random.Random(f"ps-{a.seed}-{i}")
        plan.append((persona, make_goal(menu, rng, persona), random.Random(f"psh-{a.seed}-{i}")))
    if a.dry_run:
        for i, (p, g, _) in enumerate(plan, 1):
            print(f"[{i}] {p.name} ({p.lang})\n  목표: {describe_goal(g)}\n  기대 장바구니: {g.expected}")
            if i == 1:
                print("  --- 손님 프롬프트(첫 번째 예) ---\n" + "\n".join("  " + ln for ln in build_customer_prompt(p, g).splitlines()))
        print(f"\n{len(plan)}명 (dry-run)")
        return 0
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    except ImportError:
        pass
    model = a.model or os.getenv("PERSONA_SIM_MODEL") or os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    results = []
    for i, (p, g, hrng) in enumerate(plan, 1):
        kiosk = HttpKiosk(a.url, p.lang)
        try:
            r = simulate(p, g, openai_customer(model, a.temperature, a.seed * 1000 + i), kiosk, hrng)
        finally:
            kiosk.close()
        results.append(r)
        print(f"{'PASS' if r.ok else 'FAIL'} [{i}] {p.name}  턴 {len(r.turns)}  결제 {'O' if r.paid else 'X'}  장바구니 {'O' if r.cart_ok else 'X'}")
        print(f"   목표: {r.goal_text}")
        if r.error:
            print(f"   ! {r.error}")
        if r.cart_msg:
            print(f"   - {r.cart_msg}")
        for an in r.anomalies:
            print(f"   ? {an}")
        if not r.ok:
            for n, t in enumerate(r.turns, 1):
                print(f"     T{n} 손님: {t['say']}\n        키오스크: {t['output']}  {t['actions']}")
    ok = sum(r.ok for r in results)
    print(f"\n통과 {ok}/{len(results)} (이상 패턴 {sum(len(r.anomalies) for r in results)}건)")
    dump = [{"persona": r.persona, "goal": r.goal_text, "ok": r.ok, "cart_msg": r.cart_msg, "paid": r.paid,
             "anomalies": r.anomalies, "error": r.error, "turns": r.turns} for r in results]
    if a.json:
        Path(a.json).write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.save_failed:
        Path(a.save_failed).write_text(json.dumps([d for d in dump if not d["ok"]], ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
