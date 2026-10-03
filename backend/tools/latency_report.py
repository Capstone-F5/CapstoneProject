"""시나리오 실행 결과 JSON(--json)에서 턴당 응답 시간과 가드 개입별 지연을 집계한다(LLM 호출 없음, 비용 0).

    python tools/latency_report.py out1.json out2.json

분류(한 턴이 여러 개에 해당하면 위에서부터 처음 맞는 것):
  direct   코드가 직접 처리(direct_command) — LLM을 부르지 않는다
  blocked  가드가 도구 호출을 거절(blocked) — 모델이 다시 호출하느라 LLM 왕복이 늘 수 있다
  fixed    코드가 값을 바로잡거나 빠진 일을 보완(fixed) — 추가 왕복 없이 진행
  none     가드 개입 없음
주의: 시나리오를 동시에 여러 개 실행(--workers)하면 OpenAI 응답 지연이 늘어 절대값이 커진다. 분류끼리의 비교에 쓸 것.
"""
from __future__ import annotations

import json
import statistics as st
import sys


def classify(turn: dict) -> str:
    guards = turn.get("guards") or []
    if any(g["rule"] == "direct_command" for g in guards):
        return "direct"
    if any(g.get("blocked") for g in guards):
        return "blocked"
    if any(g.get("fixed") for g in guards):
        return "fixed"
    return "none"


def pct(values: list[int], p: float) -> int:
    return sorted(values)[min(len(values) - 1, int(len(values) * p))]


def main(paths: list[str]) -> None:
    groups: dict[str, list[int]] = {"direct": [], "blocked": [], "fixed": [], "none": []}
    for path in paths:
        for r in json.load(open(path, encoding="utf-8")):
            for t in r["turns"]:
                if t.get("ms") is not None:
                    groups[classify(t)].append(t["ms"])
    everything = [ms for v in groups.values() for ms in v]
    if not everything:
        print("턴이 없다")
        return
    print(f"{'분류':<8}{'턴 수':>6}{'비율':>7}{'평균(ms)':>10}{'중앙값':>8}{'P95':>8}")
    for name, v in [("전체", everything)] + list(groups.items()):
        if v:
            print(f"{name:<8}{len(v):>6}{len(v) / len(everything):>7.0%}{st.mean(v):>10.0f}{st.median(v):>8.0f}{pct(v, .95):>8}")
    llm = groups["blocked"] + groups["fixed"] + groups["none"]
    if groups["direct"] and llm:
        print(f"\nLLM 우회(direct) 비율 {len(groups['direct']) / len(everything):.0%}, "
              f"direct 턴 중앙값 {st.median(groups['direct']):.0f}ms vs LLM 턴 중앙값 {st.median(llm):.0f}ms")
    if groups["blocked"] and groups["none"]:
        print(f"가드 거절 턴이 개입 없는 LLM 턴보다 중앙값 {st.median(groups['blocked']) - st.median(groups['none']):+.0f}ms")
    if groups["fixed"] and groups["none"]:
        print(f"가드 보정 턴이 개입 없는 LLM 턴보다 중앙값 {st.median(groups['fixed']) - st.median(groups['none']):+.0f}ms")


if __name__ == "__main__":
    main(sys.argv[1:])
