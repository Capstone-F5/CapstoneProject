#!/usr/bin/env python3
"""
키오스크 AI 시나리오 검증 도구
================================

사용법:
  python tools/scenario_runner.py                        # scenarios/ 폴더 전체 실행
  python tools/scenario_runner.py scenarios/01_*.jsonl  # 특정 시나리오만
  python tools/scenario_runner.py --url http://localhost:8000  # 서버 주소 변경

시나리오 JSONL 포맷 (한 파일 = 하나의 시나리오):
  줄 1: {"scenario": "시나리오 이름", "session_id": "test-xxx"}
  줄 2+: {"turn": N, "input": "...", "language": "ko|ja|zh|en",
           "screen": "start|orderType|menu|cart", "order_type": null|"dine-in"|"takeout",
           "cart": [...], "expect": {...}}

expect 필드:
  action_types        : list[str]  → 이 턴 actions 중 반드시 존재해야 할 type들
  no_action_types     : list[str]  → 이 턴 actions 중 존재하면 안 되는 type들
  action_value        : dict       → 특정 action이 이 값과 일치해야 함 (type+필드 검사)
  output_no_hangul    : bool       → True면 output에 한글(가-힣) 없어야
  output_asks_order_type: bool     → True면 output이 매장/포장/dine/take 관련 질문 포함
  output_max_length   : int        → output 길이(글자수) 이하여야
  note                : str        → 실패 시 출력할 설명 (검사에 영향 없음)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

# Windows 콘솔 UTF-8 출력 강제
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ── ANSI 색상 ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def ok(msg: str)   -> str: return f"{GREEN}✓{RESET} {msg}"
def fail(msg: str) -> str: return f"{RED}✗{RESET} {msg}"
def warn(msg: str) -> str: return f"{YELLOW}⚠{RESET} {msg}"
def info(msg: str) -> str: return f"{CYAN}→{RESET} {msg}"


# ── 어시션 검사기 ──────────────────────────────────────────────────────────
HANGUL_RE = re.compile(r"[가-힣]")
ORDER_TYPE_WORDS_RE = re.compile(
    r"(매장|포장|dine.?in|take.?out|店内|持ち帰り|外帯|店里|내식|테이크|to go|for here|"
    r"どちら|何処|召し上がり|내용|매장이요|포장이요|어디서|どこ)",
    re.IGNORECASE,
)


def check_assertions(
    turn_expect: dict,
    output: str,
    actions: list[dict],
    turn_num: int,
) -> list[tuple[bool, str]]:
    """(passed: bool, message: str) 튜플 리스트 반환."""
    results: list[tuple[bool, str]] = []
    action_types = {a.get("type") for a in actions}

    # action_types 포함 검사
    for required in turn_expect.get("action_types", []):
        passed = required in action_types
        results.append((passed, f"action '{required}' {'존재' if passed else '없음 ← 있어야 함'}"))

    # no_action_types 금지 검사
    for forbidden in turn_expect.get("no_action_types", []):
        passed = forbidden not in action_types
        results.append((passed, f"action '{forbidden}' {'없음 ✓' if passed else '존재 ← 없어야 함'}"))

    # action_value 상세 검사
    if av := turn_expect.get("action_value"):
        target_type = av.get("type")
        matching = [a for a in actions if a.get("type") == target_type]
        if not matching:
            results.append((False, f"action_value: type='{target_type}' 없음"))
        else:
            a = matching[0]
            for k, v in av.items():
                if k == "type":
                    continue
                actual = a.get(k)
                passed = actual == v
                results.append((passed, f"action[{target_type}].{k}: {actual!r} {'==' if passed else '!='} {v!r}"))

    # 한글 없음 검사
    if turn_expect.get("output_no_hangul"):
        has_hangul = bool(HANGUL_RE.search(output))
        results.append((not has_hangul, f"output에 한글 {'있음 ← 없어야 함' if has_hangul else '없음 ✓'}"))
        if has_hangul:
            # 어떤 한글인지 보여주기
            hangul_parts = re.findall(r"[가-힣]+", output)
            results.append((False, f"  한글 단어: {hangul_parts[:5]}"))

    # 매장/포장 질문 포함 검사
    if turn_expect.get("output_asks_order_type"):
        has_q = bool(ORDER_TYPE_WORDS_RE.search(output))
        results.append((has_q, f"output이 매장/포장 질문 {'포함 ✓' if has_q else '없음 ← 있어야 함'}"))

    # 최대 길이 검사
    if max_len := turn_expect.get("output_max_length"):
        actual_len = len(output)
        passed = actual_len <= max_len
        results.append((passed, f"output 길이: {actual_len}자 {'<=' if passed else '>'} {max_len}자"))

    return results


# ── API 호출 ───────────────────────────────────────────────────────────────
def call_llm(base_url: str, session_id: str, turn: dict) -> dict:
    """POST /ai_modules/llm 호출 후 {output, actions} 반환."""
    payload = {
        "session_id": session_id,
        "input":      turn["input"],
        "language":   turn.get("language"),
        "screen":     turn.get("screen"),
        "order_type": turn.get("order_type"),
        "cart":       turn.get("cart", []),
    }
    resp = httpx.post(f"{base_url}/ai_modules/llm", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def reset_session(base_url: str, session_id: str) -> None:
    httpx.post(f"{base_url}/ai_modules/llm/reset", params={"session_id": session_id}, timeout=10)


# ── 시나리오 파일 파서 ─────────────────────────────────────────────────────
def load_scenario(path: Path) -> tuple[dict, list[dict]]:
    """(header, turns) 반환. header = 첫 줄, turns = 나머지."""
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"{path}: 빈 파일")
    header = json.loads(lines[0])
    turns  = [json.loads(ln) for ln in lines[1:]]
    return header, turns


# ── 시나리오 실행 ──────────────────────────────────────────────────────────
def run_scenario(path: Path, base_url: str, verbose: bool = False) -> tuple[int, int]:
    """(passed, total) 반환."""
    header, turns = load_scenario(path)
    scenario_name = header.get("scenario", path.stem)
    # session_id를 매번 고유하게 생성해 메모리가 섞이지 않도록
    session_id = f"{header.get('session_id', 'test')}-{uuid.uuid4().hex[:6]}"

    print(f"\n{BOLD}{CYAN}━━ {scenario_name} ━━{RESET}")
    print(f"{GRAY}  session: {session_id}  file: {path.name}{RESET}")

    reset_session(base_url, session_id)

    passed_total = 0
    check_total  = 0

    for turn in turns:
        n   = turn.get("turn", "?")
        inp = turn.get("input", "")
        exp = turn.get("expect", {})
        note = exp.get("note", "")

        print(f"\n  {BOLD}Turn {n}{RESET}: {GRAY}\"{inp}\"{RESET}")
        if note:
            print(f"  {GRAY}기대: {note}{RESET}")

        try:
            t0  = time.monotonic()
            res = call_llm(base_url, session_id, turn)
            ms  = int((time.monotonic() - t0) * 1000)
        except httpx.HTTPStatusError as e:
            print(f"  {fail(f'API 오류 {e.response.status_code}: {e.response.text[:120]}')}")
            check_total += 1
            continue
        except Exception as e:
            print(f"  {fail(f'요청 실패: {e}')}")
            check_total += 1
            continue

        output  = res.get("output", "")
        actions = res.get("actions", [])

        # 응답 출력
        print(f"  {GRAY}응답({ms}ms, {len(output)}자):{RESET} {output[:120]}{'…' if len(output)>120 else ''}")
        if actions:
            for a in actions:
                print(f"  {GRAY}action:{RESET} {json.dumps(a, ensure_ascii=False)[:100]}")

        # 어시션 검사
        checks = check_assertions(exp, output, actions, n)
        for passed, msg in checks:
            check_total += 1
            if passed:
                passed_total += 1
                if verbose:
                    print(f"    {ok(msg)}")
            else:
                print(f"    {fail(msg)}")

        if not checks:
            print(f"    {GRAY}(어시션 없음){RESET}")

    return passed_total, check_total


# ── main ───────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="키오스크 AI 시나리오 검증 도구")
    parser.add_argument(
        "files", nargs="*",
        help="실행할 시나리오 JSONL 파일. 미지정 시 scenarios/ 폴더 전체"
    )
    parser.add_argument("--url", default="http://localhost:8000", help="백엔드 서버 주소")
    parser.add_argument("-v", "--verbose", action="store_true", help="성공한 검사도 출력")
    args = parser.parse_args()

    # 파일 목록 결정
    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        base = Path(__file__).parent / "scenarios"
        paths = sorted(base.glob("*.jsonl"))

    if not paths:
        print(warn("실행할 시나리오 파일이 없습니다."))
        sys.exit(1)

    # 서버 연결 확인
    try:
        httpx.get(f"{args.url}/health", timeout=5).raise_for_status()
        print(ok(f"서버 연결 확인: {args.url}"))
    except Exception as e:
        print(fail(f"서버 연결 실패: {e}"))
        print(info("백엔드 서버가 실행 중인지 확인하세요: uvicorn main:app --reload"))
        sys.exit(1)

    grand_passed = 0
    grand_total  = 0
    failed_scenarios: list[str] = []

    for path in paths:
        try:
            p, t = run_scenario(path, args.url, verbose=args.verbose)
            grand_passed += p
            grand_total  += t
            if p < t:
                failed_scenarios.append(path.name)
        except Exception as e:
            print(f"\n{fail(f'{path.name} 파싱/실행 오류: {e}')}")

    # 최종 요약
    print(f"\n{BOLD}━━━━━━━━━━━━━━ 결과 요약 ━━━━━━━━━━━━━━{RESET}")
    pct = int(grand_passed / grand_total * 100) if grand_total else 0
    color = GREEN if pct == 100 else (YELLOW if pct >= 70 else RED)
    print(f"  {color}{BOLD}{grand_passed}/{grand_total} 검사 통과 ({pct}%){RESET}")
    if failed_scenarios:
        print(f"  {RED}실패한 시나리오:{RESET}")
        for s in failed_scenarios:
            print(f"    - {s}")
    else:
        print(f"  {GREEN}모든 시나리오 통과!{RESET}")

    sys.exit(0 if not failed_scenarios else 1)


if __name__ == "__main__":
    main()
