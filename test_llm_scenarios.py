"""
LLM 시나리오 테스트 스크립트.
사용법: python test_llm_scenarios.py (프로젝트 루트에서 실행)
"""
import sys
import os
import asyncio

# ── 경로 설정 (main.py 패턴 그대로) ─────────────────────────────────────────
_project_root = os.path.dirname(os.path.abspath(__file__))
_backend_dir  = os.path.join(_project_root, "backend")
sys.path.insert(0, _project_root)
sys.path.insert(0, _backend_dir)

# ── .env 로드 ────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

# ── 이제 프로젝트 모듈 임포트 가능 ───────────────────────────────────────────
from backend.core.llm_service import run_agent   # type: ignore


# ── 시나리오 정의 ────────────────────────────────────────────────────────────

CART_C = [
    {
        "cart_id": 1234,
        "menu_id": 2,
        "name": "불고기버거",
        "item_type": "single",
        "quantity": 2,
        "unit_price": 4500,
        "exclusion": "없음",
        "side": None,
        "drink": None,
    },
    {
        "cart_id": 5678,
        "menu_id": 17,
        "name": "코카콜라",
        "item_type": "single",
        "quantity": 1,
        "unit_price": 2000,
        "exclusion": "없음",
        "side": None,
        "drink": None,
    },
]

SCENARIOS = [
    # ── Group A ──
    {
        "id": "A1",
        "session_id": "test-group-A",
        "input": "불고기버거 하나 주세요",
        "language": "ko",
        "cart": [],
        "screen": "start",
        "order_type": None,
    },
    {
        "id": "A2",
        "session_id": "test-group-A2",
        "input": "뭐 먹을지 모르겠어요",
        "language": "ko",
        "cart": [],
        "screen": "start",
        "order_type": None,
    },
    {
        "id": "A3",
        "session_id": "test-group-A3",
        "input": "버거 메뉴 보여줘",
        "language": "ko",
        "cart": [],
        "screen": "start",
        "order_type": None,
    },
    # ── Group B ──
    {
        "id": "B1",
        "session_id": "test-group-B1",
        "input": "치즈버거 세트 주세요",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    {
        "id": "B2",
        "session_id": "test-group-B2",
        "input": "F버거 하나 주세요",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    {
        "id": "B3",
        "session_id": "test-group-B3",
        "input": "불고기버거 두 개 주세요",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    {
        "id": "B4",
        "session_id": "test-group-B4",
        "input": "버거 뭐 있어?",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    {
        "id": "B5",
        "session_id": "test-group-B5",
        "input": "피자 주세요",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    {
        "id": "B6",
        "session_id": "test-group-B6",
        "input": "버거 줘",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    # ── Group C ──
    {
        "id": "C1",
        "session_id": "test-group-C1",
        "input": "불고기버거 3개로 바꿔줘",
        "language": "ko",
        "cart": CART_C,
        "screen": "cart",
        "order_type": "dine-in",
    },
    {
        "id": "C2",
        "session_id": "test-group-C2",
        "input": "콜라 빼줘",
        "language": "ko",
        "cart": CART_C,
        "screen": "cart",
        "order_type": "dine-in",
    },
    {
        "id": "C3",
        "session_id": "test-group-C3",
        "input": "결제할게",
        "language": "ko",
        "cart": CART_C,
        "screen": "cart",
        "order_type": "dine-in",
    },
    {
        "id": "C4",
        "session_id": "test-group-C4",
        "input": "카드로 결제할게",
        "language": "ko",
        "cart": CART_C,
        "screen": "cart",
        "order_type": "dine-in",
    },
    # ── Group D ──
    {
        "id": "D1",
        "session_id": "test-group-D1",
        "input": "불고기버거 반으로 잘라주세요",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    {
        "id": "D2",
        "session_id": "test-group-D2",
        "input": "치즈버거 세트 사이다로, 콜라도 하나",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
    {
        "id": "D3",
        "session_id": "test-group-D3",
        "input": "영어로 얘기해도 돼?",
        "language": "ko",
        "cart": [],
        "screen": "menu",
        "order_type": "dine-in",
    },
]


async def run_scenario(s: dict) -> dict:
    result = await run_agent(
        session_id=s["session_id"],
        user_input=s["input"],
        language=s.get("language"),
        cart=s.get("cart", []),
        screen=s.get("screen"),
        order_type=s.get("order_type"),
    )
    return result


async def main():
    for s in SCENARIOS:
        print(f"\n=== [{s['id']}] ===")
        print(f"INPUT: {s['input']}")
        try:
            result = await run_scenario(s)
            print(f"OUTPUT: {result.get('output', '(없음)')}")
            actions = result.get("actions", [])
            if actions:
                import json
                print(f"ACTIONS: {json.dumps(actions, ensure_ascii=False, indent=2)}")
            else:
                print("ACTIONS: []")
        except Exception as e:
            import traceback
            print(f"OUTPUT: [ERROR] {e}")
            print(f"ACTIONS: []")
            traceback.print_exc()


if __name__ == "__main__":
    import io
    # Force UTF-8 stdout so Korean text is not mangled on Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    asyncio.run(main())
