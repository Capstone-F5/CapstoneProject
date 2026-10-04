"""LLM을 거치되, 코드가 발화에서 읽은 도구 호출을 모델에게 강하게 제안하는 힌트.

문장이 "메뉴 이름 + 수량 (+ 단품)"뿐인 단순 주문이면 파서(order_parser.parse_simple_order)가 어떤 메뉴를 몇 개 담아야 하는지
확신한다. 그 결과(메뉴 UUID 포함)를 모델 입력 뒤에 붙이면, 모델이 menu_item_id 자리에 이름을 넣거나 다른 메뉴의 id를 재사용하는
사고(가드 개입 1위 `id_is_name`)와 그에 따른 거절·재시도를 처음부터 피할 수 있다. 모델의 응답은 그대로 쓰므로 자연스러운 안내문과
다국어 처리는 유지된다. 힌트를 줬는데도 담지 않으면 llm_service가 한 번 더 질의하고, 그래도 안 되면 기존 코드 보완이 이어받는다.
파서가 확신하지 못하면 힌트를 붙이지 않는다("모르면 개입하지 않는다").
"""
from __future__ import annotations

from ai_modules.llm import guards, order_parser


def build_hint(user_input: str, menu: list[dict], last_bot: str = "") -> dict | None:
    """{"text": 모델 입력에 붙일 힌트, "expected": [(menu_item_id, 이름, 수량), ...]} 또는 None."""
    if order_parser.awaiting_set_option(last_bot):
        return None   # 세트의 사이드·음료를 고르는 중이다("콜라로 주세요"는 단품 주문이 아니다)
    parsed = order_parser.parse_simple_order(user_input, menu)
    if not parsed:
        return None
    expected = [(item["id"], item["name_ko"], qty) for item, qty in parsed]
    calls = "; ".join(f'add_item(menu_item_id="{mid}", quantity={qty}) — {name}' for mid, name, qty in expected)
    text = (
        "\n\n[시스템 힌트(코드가 발화를 분석함): 손님은 다음 품목을 단품으로 담아 달라고 했다. "
        f"{calls}. 품목마다 정확히 한 번씩, menu_item_id는 위 UUID를 그대로 사용해 호출한다(메뉴 이름을 넣지 않는다). "
        "호출이 끝나면 결과를 짧게 안내한다.]"
    )
    return {"text": text, "expected": expected}


def missing_items(hint: dict, actions: list[dict]) -> list[tuple[str, str, int]]:
    """힌트가 제안한 품목 중 이번 턴에 add_item으로 담기지 않은 것."""
    added = {a.get("menu_item_id") for a in actions if a.get("type") == "add_item"}
    return [e for e in hint["expected"] if e[0] not in added]


def retry_text(missing: list[tuple[str, str, int]], previous_output: str) -> str:
    """재질의 입력에 붙일 더 강한 지시. 이미 담긴 품목은 빼고 빠진 것만 가리킨다."""
    calls = "; ".join(f'add_item(menu_item_id="{mid}", quantity={qty}) — {name}' for mid, name, qty in missing)
    return (
        f"\n\n[시스템 지시: 직전 응답({previous_output[:60]!r})은 잘못됐다. 손님이 말한 품목이 아직 장바구니에 담기지 않았다. "
        f"지금 반드시 다음을 호출하라: {calls}. 호출 없이 '담았습니다'·'품절'·'메뉴에 없습니다'라고 답하지 않는다. "
        "이미 담긴 품목은 다시 담지 않는다.]"
    )
