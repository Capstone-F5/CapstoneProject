"""음성 시나리오 실행 결과를 정직하게 집계하는 순수 함수들(서버·LLM 불필요).

문제: 시나리오는 "매 턴 장바구니가 기대와 정확히 같아야 함"으로 판정하므로 한 번 어긋나면 이후 턴이 모두 실패로 잡힌다
(음성 검증 50개: 턴 실패 147건 중 대부분이 연쇄, 시나리오별 첫 실패는 36건). 그래서
  - 엄격(strict): 지금까지의 방식 — 한 턴이라도 틀리면 시나리오 실패
  - 이어가기(resync): 앞에서 생긴 불일치는 그대로 두고 **새로 생긴 불일치**만 그 턴의 실패로 센다
  - 부분 통과(SOFT): 교체 명령에서 A만 지우고 B를 되묻는 응답(삭제 후 확인) — 실패는 아니지만 통과도 아님
세 가지를 함께 낸다. 조작별 실패율에는 Wilson 신뢰구간을 붙인다(표본이 작아서 점추정만으로는 오해하기 쉽다).
"""
from __future__ import annotations

import math
import re
from typing import Iterable

_ASKS_ADD = re.compile(r"담아\s*드릴까요|담을까요|담아\s*드릴게요\?|추가할까요|주문하시겠어요|담아줄까요")


def _norm(s: str) -> str:
    return re.sub(r"[\s()（）]", "", s or "").lower()


def _key(name: str, opts: Iterable[str]):
    return (_norm(name), tuple(sorted(_norm(o) for o in opts)))


def counts_from_cart(cart: list[dict]) -> dict:
    """voice_scenario_suite.cart_snapshot 결과 → {(이름, 옵션들): 수량}. 같은 구성은 합산한다."""
    out: dict = {}
    for c in cart:
        k = _key(c["name"], c["opts"])
        out[k] = out.get(k, 0) + c["qty"]
    return out


def counts_from_expected(expected: list[dict]) -> dict:
    out: dict = {}
    for e in expected:
        k = _key(e["name"], e["opts"])
        out[k] = out.get(k, 0) + e["qty"]
    return out


def diff(got: dict, want: dict) -> dict:
    """실제 − 기대. 0이 아닌 항목만."""
    keys = set(got) | set(want)
    return {k: got.get(k, 0) - want.get(k, 0) for k in keys if got.get(k, 0) != want.get(k, 0)}


def new_discrepancy(d_new: dict, d_prev: dict) -> bool:
    """이번 턴에서 불일치가 새로 생기거나 커졌는가. 이미 있던 불일치가 그대로이거나 줄어든 것은 새 실패가 아니다
    (예: 앞에서 빠진 줄을 손님이 나중에 지우는 기대 → 불일치가 해소됨)."""
    for k, v in d_new.items():
        if abs(v) > abs(d_prev.get(k, 0)) or (k in d_prev and (v > 0) != (d_prev[k] > 0)):
            return True
    return False


def is_soft_replace(before: dict, after: dict, action_types: list[str], output: str) -> bool:
    """교체 명령("A 말고 B로")에서 A만 사라지고 아무것도 추가되지 않았으며, 응답이 B를 담을지 되묻는 경우."""
    if "add_item" in action_types or "remove_item" not in action_types:
        return False
    removed = {k: before.get(k, 0) - after.get(k, 0) for k in before if before.get(k, 0) > after.get(k, 0)}
    added = [k for k in after if after[k] > before.get(k, 0)]
    return bool(removed) and not added and bool(_ASKS_ADD.search(output or ""))


def scenario_status(turns: list[dict]) -> str:
    """PASS: 새 실패 없음 / SOFT: 부분 통과 턴만 있음 / FAIL: 실제 새 실패가 있음."""
    if any(t.get("real_fail") for t in turns):
        return "FAIL"
    if any(t.get("soft_fail") for t in turns):
        return "SOFT"
    return "PASS"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p))]


def summarize(results: list[dict]) -> dict:
    """results: [{ok, status, turns:[{op, fails, real_fail, soft_fail, ms}]}].
    반환: 시나리오 집계, 턴당 첫 실패율(엄격/이어가기), 조작별 실패율(이어가기)과 신뢰구간, 응답 시간."""
    n = len(results)
    status = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "SOFT", "FAIL")}
    strict_ok = sum(1 for r in results if r["ok"])

    def hazard(fail_key):
        fails = turns_seen = 0
        for r in results:
            for t in r["turns"]:
                turns_seen += 1
                bad = t.get("fails") if fail_key == "strict" else (t.get("real_fail") or t.get("soft_fail"))
                if bad:
                    fails += 1
                    break
        return fails, turns_seen

    sf, st = hazard("strict")
    rf, rt = 0, 0
    for r in results:   # 이어가기: 실패해도 끝까지 본다 — 모든 턴이 분모, 새 실패(real/soft)가 분자
        for t in r["turns"]:
            rt += 1
            rf += bool(t.get("real_fail") or t.get("soft_fail"))
    per_op: dict[str, list[int]] = {}
    for r in results:
        for t in r["turns"]:
            if t.get("op"):
                row = per_op.setdefault(t["op"], [0, 0, 0])
                row[0] += 1
                row[1] += bool(t.get("real_fail"))
                row[2] += bool(t.get("soft_fail"))
    ms = [t["ms"] for r in results for t in r["turns"] if t.get("ms")]
    return {
        "scenarios": n, "strict_pass": strict_ok, "status": status,
        "strict_first_fail": (sf, st), "resync_new_fail": (rf, rt),
        "per_op": {op: {"n": v[0], "fail": v[1], "soft": v[2], "ci": wilson(v[1] + v[2], v[0])} for op, v in per_op.items()},
        "latency": {"p50": percentile(ms, 0.5), "p90": percentile(ms, 0.9), "max": max(ms) if ms else 0},
    }


def format_summary(s: dict) -> str:
    n = s["scenarios"]
    st = s["status"]
    lines = [
        f"엄격 판정(한 턴이라도 틀리면 실패): {s['strict_pass']}/{n} ({100 * s['strict_pass'] / max(n, 1):.0f}%)",
        f"이어가기 판정(새 불일치만 실패): PASS {st['PASS']} / SOFT {st['SOFT']} / FAIL {st['FAIL']}  "
        f"→ PASS+SOFT {100 * (st['PASS'] + st['SOFT']) / max(n, 1):.0f}%, PASS만 {100 * st['PASS'] / max(n, 1):.0f}%",
        f"턴당 엄격 첫 실패율: {s['strict_first_fail'][0]}/{s['strict_first_fail'][1]} = {100 * s['strict_first_fail'][0] / max(s['strict_first_fail'][1], 1):.1f}%"
        f"  |  이어가기 새 실패율: {s['resync_new_fail'][0]}/{s['resync_new_fail'][1]} = {100 * s['resync_new_fail'][0] / max(s['resync_new_fail'][1], 1):.1f}%",
        f"응답 시간: p50 {s['latency']['p50'] / 1000:.1f}s  p90 {s['latency']['p90'] / 1000:.1f}s  max {s['latency']['max'] / 1000:.1f}s",
        "", "조작별 새 실패율(이어가기, 95% 구간) — 표본이 작으면 구간이 넓다",
    ]
    for op, v in sorted(s["per_op"].items(), key=lambda kv: -(kv[1]["fail"] + kv[1]["soft"]) / kv[1]["n"]):
        lo, hi = v["ci"]
        soft = f" (SOFT {v['soft']})" if v["soft"] else ""
        lines.append(f"  {op:<18} {v['fail'] + v['soft']:>3}/{v['n']:<3} {100 * (v['fail'] + v['soft']) / v['n']:>3.0f}%  [{100 * lo:.0f}–{100 * hi:.0f}%]{soft}")
    return "\n".join(lines)
