"""
LangChain Agent 실행 래퍼.

- 요청 단위로 session_id / cart ContextVar 를 세팅.
- ConversationSummaryBufferMemory 로 대화 맥락 유지.
- 스트림 종료 후 발행된 액션을 SSE 로 일괄 전송.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from langchain_core.messages import SystemMessage

from ai_modules.llm.action_context import get_actions, reset_actions, set_cart
from ai_modules.llm.agent import get_agent_executor
from ai_modules.llm.memory import get_memory
from ai_modules.llm.session_context import set_session_id

# 감지된 언어로 답변하도록 지시하는 SystemMessage 텍스트.
# ko/zh/ja 는 UI 지원 언어이므로 해당 언어 고정.
# "en" 버킷은 영어 + UI 미지원 언어(독일어/프랑스어 등 라틴 문자) 공용 —
# UI는 영어로 표시되지만 답변은 사용자가 실제 쓴 언어에 맞춘다(LLM이 입력 텍스트로 판별).
_LANG_INSTRUCTIONS: dict[str, str] = {
    "ko": "사용자는 한국어로 말하고 있습니다. 반드시 한국어로만 답변하세요. 메뉴 이름은 원래 표기 그대로 사용합니다.",
    "en": (
        "The kiosk UI is displayed in English. Reply in the SAME language the user is actually "
        "using in their message: if they write in English, reply in English; if they write in "
        "another language such as German, French, Spanish or Vietnamese, reply in that same language. "
        "Keep all menu item names in their original Korean form, and always state prices in Korean won "
        "(e.g., 4,500 won)."
    ),
    "zh": "用户正在使用中文。请务必只用中文回答。菜单名称保留原文，价格一律用韩元表示（例如 4500 韩元）。",
    "ja": "ユーザーは日本語で話しています。必ず日本語のみで答えてください。メニュー名は元の表記のまま使い、価格は必ず韓国ウォンで表記してください（例: 4,500ウォン）。",
}
# ko / zh / ja 외 모든 언어는 영어로 처리
_NATIVE_LANGS = frozenset({"ko", "zh", "ja"})


def _prepend_language(chat_history: list, language: str | None) -> list:
    """감지된 언어 코드가 있으면 히스토리 맨 앞에 기본 언어 SystemMessage를 주입."""
    if not language:
        return chat_history
    normalized = language if language in _NATIVE_LANGS else "en"
    instruction = _LANG_INSTRUCTIONS.get(normalized)
    if not instruction:
        return chat_history
    return [SystemMessage(content=instruction)] + chat_history


def _cart_summary(cart: list) -> str:
    """장바구니 스냅샷을 사람이 읽는 요약 문자열로 변환."""
    if not cart:
        return "현재 장바구니: 비어 있음"
    lines = ["현재 장바구니: (수정/삭제 시 cart_id로 정확한 줄을 지정)"]
    total = 0
    for c in cart:
        name = c.get("name") or f"메뉴#{c.get('menu_id')}"
        qty = c.get("quantity", 1)
        price = c.get("unit_price", 0)
        subtotal = qty * price
        total += subtotal
        type_label = "세트" if c.get("item_type") == "set" else "단품"
        excl = c.get("exclusion", "없음")
        cid = c.get("cart_id")
        line = f"  - cart_id={cid} | menu_id={c.get('menu_id')} | {name}({type_label}) x{qty}  소계 {subtotal}원"
        if excl and excl != "없음":
            line += f"  [{excl}]"
        side = c.get("side")
        drink = c.get("drink")
        if side or drink:
            line += f"  [사이드:{side} / 음료:{drink}]"
        lines.append(line)
    lines.append(f"  합계: {total}원")
    return "\n".join(lines)


# 화면별 가능 동작 짧은 안내 (프롬프트 [화면별 가능 동작] 과 일치시켜 유지)
_SCREEN_HINT: dict[str, str] = {
    "start": "navigate('orderType')로 주문 시작, set_language/set_gesture/set_camera 가능.",
    "orderType": "ui_action order_type(dine-in|takeout)로 매장/포장 선택.",
    "menu": "add_item으로 담기, ui_action select_category/menu_page/open_item, navigate('cart').",
    "cart": "update_qty/remove_item/clear_cart, ui_action start_checkout/points/points_phone/payment_method.",
    "complete": "navigate('start')로 새 주문.",
}


def _context_message(cart: list, screen: str | None, order_type: str | None = None,
                     modal_state: dict | None = None) -> str:
    """현재 화면 + 주문 유형 + 가능 동작 + 장바구니 요약을 합친 컨텍스트 메시지."""
    parts: list[str] = []
    if screen:
        hint = _SCREEN_HINT.get(screen, "")
        parts.append(f"현재 화면: {screen}" + (f" — 가능 동작: {hint}" if hint else ""))
    if order_type:
        label = "매장 식사" if order_type == "dine-in" else "포장"
        parts.append(f"주문 유형: {label}")
    else:
        parts.append("주문 유형: 미선택 (매장/포장 아직 고르지 않음)")
    if modal_state:
        ms = modal_state
        type_label = "세트" if ms.get("item_type") == "set" else "단품"
        parts.append(
            f"현재 열린 팝업: {ms.get('name', '')} {type_label} — "
            f"수량 {ms.get('qty', 1)}개, "
            f"제외 {ms.get('exclusion') or '없음'}, "
            f"사이드 {ms.get('side') or '미선택'}, "
            f"음료 {ms.get('drink') or '미선택'}"
        )
    parts.append(_cart_summary(cart))
    return "\n".join(parts)


async def run_agent_stream(
    session_id: str,
    user_input: str,
    language: str | None = None,
    cart: list | None = None,
    screen: str | None = None,
    order_type: str | None = None,
    modal_state: dict | None = None,
) -> AsyncIterator[str]:
    """LLM 응답을 SSE(text/event-stream) 형식으로 토큰 단위 yield.

    최종 답변 토큰만 스트리밍(툴 호출 중 LLM 출력은 제외).
    스트림 종료 후 발행된 액션을 data:{"action":...} 으로 전송.
    마지막에 data: {"done": true, "output": "..."} 전송.
    """
    cart = cart or []
    set_session_id(session_id)
    set_cart(cart)
    reset_actions()

    memory = await get_memory(session_id)
    executor = get_agent_executor()

    mem_vars = await memory.aload_memory_variables({})
    chat_history = _prepend_language(
        mem_vars.get("chat_history", []), language
    )

    # 현재 화면 + 주문 유형 + 팝업 상태 + 장바구니 요약을 chat_history 앞에 SystemMessage 로 주입
    chat_history = [SystemMessage(content=_context_message(cart, screen, order_type, modal_state))] + chat_history

    output_parts: list[str] = []
    in_tool_call = False
    emitted_count = 0  # 이미 인라인으로 전송한 액션 수 추적

    async for event in executor.astream_events(
        {"input": user_input, "chat_history": chat_history},
        version="v1",
    ):
        kind = event["event"]

        if kind == "on_tool_start":
            in_tool_call = True

        elif kind == "on_tool_end":
            in_tool_call = False
            # 도구 실행 즉시 새로 쌓인 액션을 SSE 로 내보냄
            # → 텍스트 토큰보다 먼저 프론트에 도달 → 화면 이동이 응답 텍스트보다 앞서 발생
            current_actions = get_actions()
            if len(current_actions) > emitted_count:
                for action in current_actions[emitted_count:]:
                    yield f"data: {json.dumps({'action': action}, ensure_ascii=False)}\n\n"
                emitted_count = len(current_actions)

        elif kind == "on_chat_model_stream" and not in_tool_call:
            chunk = event["data"]["chunk"]
            content: str = getattr(chunk, "content", "") or ""
            tool_calls = getattr(chunk, "additional_kwargs", {}).get("tool_calls")
            if content and not tool_calls:
                output_parts.append(content)
                yield f"data: {json.dumps({'token': content}, ensure_ascii=False)}\n\n"

    output = "".join(output_parts)
    await memory.asave_context({"input": user_input}, {"output": output})

    # 인라인으로 아직 전송되지 않은 나머지 액션 전송 (안전장치)
    remaining = get_actions()[emitted_count:]
    for action in remaining:
        yield f"data: {json.dumps({'action': action}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'done': True, 'output': output}, ensure_ascii=False)}\n\n"


async def run_agent(
    session_id: str,
    user_input: str,
    language: str | None = None,
    cart: list | None = None,
    screen: str | None = None,
    order_type: str | None = None,
    modal_state: dict | None = None,
) -> dict[str, Any]:
    cart = cart or []
    set_session_id(session_id)
    set_cart(cart)
    reset_actions()

    memory = await get_memory(session_id)
    executor = get_agent_executor()

    mem_vars = await memory.aload_memory_variables({})
    chat_history = _prepend_language(
        mem_vars.get("chat_history", []), language
    )

    chat_history = [SystemMessage(content=_context_message(cart, screen, order_type, modal_state))] + chat_history

    result = await executor.ainvoke(
        {"input": user_input, "chat_history": chat_history}
    )
    output = result.get("output", "")

    await memory.asave_context({"input": user_input}, {"output": output})

    return {
        "session_id": session_id,
        "output": output,
        "actions": get_actions(),
        "intermediate_steps": [
            {
                "tool": getattr(step[0], "tool", str(step[0])),
                "tool_input": getattr(step[0], "tool_input", None),
                "result": step[1],
            }
            for step in result.get("intermediate_steps", [])
        ],
    }
