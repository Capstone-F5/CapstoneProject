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

from core.cart_context import (
    cart_summary as _cart_summary,
    format_cart_status_reply,
    is_cart_status_query,
)
from ai_modules.llm.action_context import (
    get_actions, reset_actions, set_cart, set_user_input, set_checkout_snapshot, set_last_bot_text,
    set_stt_original, set_recent_user_text, reset_guards, record_guard, get_guard_hits,
)
from ai_modules.llm.guards import NOISE_REPLY, correct_reply, fix_stt, guard_mode, is_noise
from ai_modules.llm.agent import get_agent_executor
from ai_modules.llm.checkout_progress import snapshot as checkout_snapshot
from .intent_fallback import ensure_actions
from ai_modules.llm.memory import get_memory, save_and_prune
from ai_modules.llm.session_context import set_session_id
from ai_modules.llm.rag import get_active_discount_context
from .conversation_log import log_turn

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
    "ja": "ユーザーは日本語で話しています。必ず日本語のみで答えてください。メニュー名は必ず日本語のカタカナに翻訳してください（例: 치즈버거→チーズバーガー、감자튀김→フライドポテト、F버거→Fバーガー、콜라→コーラ）。韓国語の한글文字を返答に含めてはいけません。価格は必ず韓国ウォンで表記してください（例: 4,500ウォン）。",
}
# ko / zh / ja 외 모든 언어는 영어로 처리
_NATIVE_LANGS = frozenset({"ko", "zh", "ja"})

# LLM 호출 자체가 실패했을 때(메모리 로드/네트워크/속도 제한 등) 보여줄 안내문 — LLM이 생성하는
# 문장이 아니라 고정 문자열이므로 UI 지원 4개 언어로만 준비하고, 나머지는 영어로 대체한다.
_FALLBACK_MESSAGES: dict[str, str] = {
    "ko": "죄송해요, 지금 답변을 생성하지 못했어요. 다시 한번 말씀해 주세요.",
    "en": "Sorry, I couldn't generate a response just now. Please try saying that again.",
    "zh": "抱歉，现在无法生成回复。请再说一次。",
    "ja": "申し訳ございません、只今応答を生成できませんでした。もう一度お話しください。",
}


def _remember_history(mem_vars: dict) -> None:
    """가드가 쓰는 대화 맥락을 저장한다: 직전 키오스크 안내, 직전 손님 말 몇 턴.
    ("맞아요" 같은 이름 없는 확인 답변이나 여러 턴에 걸쳐 말한 사이드·음료를 규칙으로 따질 때 필요)"""
    history = mem_vars.get("chat_history", []) or []
    last_bot = next((str(getattr(m, "content", "")) for m in reversed(history) if getattr(m, "type", "") == "ai"), "")
    humans = [str(getattr(m, "content", "")) for m in history if getattr(m, "type", "") == "human"]
    set_last_bot_text(last_bot)
    set_recent_user_text(" ".join(humans[-3:]))


def _align_reply_with_actions(output: str) -> str:
    """"담았습니다/삭제했습니다/변경했습니다"라고 하는데 이번 턴에 그에 맞는 액션이 없으면 안전한 문구로 바꾼다.
    (스트리밍에서는 이미 읽힌 음성은 되돌릴 수 없고, 화면 텍스트와 대화 기록이 바로잡힌다)"""
    if guard_mode() == "off":
        return output
    fixed = correct_reply(output, [a.get("type") for a in get_actions()])
    if not fixed:
        return output
    enforcing = guard_mode() == "enforce"
    record_guard("reply_without_action", f"응답 「{output[:40]}」에 맞는 액션 없음", blocked=enforcing)
    return fixed if enforcing else output


def _fallback_message(language: str | None) -> str:
    normalized = language if language in _NATIVE_LANGS else "en"
    return _FALLBACK_MESSAGES.get(normalized, _FALLBACK_MESSAGES["en"])


# 응답 언어 알림 — 도구 결과가 한국어로 와서 영어/일본어/중국어 손님에게도 한국어로 답하는 것을 막는다.
# 시스템 지시는 대화 맨 앞에 있어 도구 호출을 거치면 약해지므로, 질문 바로 뒤에 짧게 한 번 더 붙인다.
# (메모리에는 원문만 저장하고, 모델 입력에만 붙인다.)
_LANG_REMINDERS: dict[str, str] = {
    "en": "\n\n[Reply in English (or the user's own language) — not Korean. Menu item names may stay in Korean.]",
    "ja": "\n\n[必ず日本語で答えてください。韓国語の文は使わないでください。]",
    "zh": "\n\n[请务必用中文回答，不要使用韩语句子。]",
}


def _modal_reminder(modal_state: dict | None) -> str:
    """팝업이 열려 있으면 질문 바로 뒤에 처리 방법을 한 번 더 알린다.

    시스템 쪽 컨텍스트만으로는 "두 개로 해줘"처럼 대상이 생략된 발화를 장바구니 질문으로 오해하는 경우가
    있어서, 모델 입력에만 붙인다(메모리에는 원문만 저장).
    """
    if not modal_state:
        return ""
    return (
        f"\n\n[화면에 '{modal_state.get('name', '')}' 옵션 팝업이 열려 있음. 대상이 생략된 수량·사이드·음료·제외 "
        "요청은 이 팝업에 대한 것이다 — 장바구니가 비어 있어도 팝업 기준으로 update_modal을 호출하고, "
        "손님이 '담아줘/이대로' 등으로 담기를 분명히 말하기 전에는 add_item을 호출하지 않는다. "
        "단품→세트 전환은 open_item(item_type=set)으로 처리한다.]"
    )


def _agent_input(user_input: str, language: str | None, modal_state: dict | None = None) -> str:
    return user_input + _LANG_REMINDERS.get(language or "", "") + _modal_reminder(modal_state)


def _resolve_language(declared: str | None, text: str) -> str | None:
    """요청이 선언한 언어와 실제 입력 문자를 대조해 이번 턴의 응답 언어를 정한다.

    프론트는 세션 첫 발화에서 감지한 언어를 이후 모든 요청에 고정해 보낸다. 그래서 한국어로 시작한
    세션에서 손님이 영어로 말하면 "한국어로 답하라"는 지시가 계속 붙어 한국어 답이 온다. 또
    language가 없으면 지시가 없어 모델이 한국어 프롬프트·한국어 도구 결과에 끌려 한국어로 답한다.
    문자 구성이 분명할 때만 선언을 덮어쓰고, 모호한 짧은 입력("네", "OK", 숫자)은 선언을 따른다.
    """
    t = text or ""
    hangul = sum(1 for c in t if "가" <= c <= "힣")
    kana = sum(1 for c in t if "぀" <= c <= "ヿ")
    han = sum(1 for c in t if "一" <= c <= "鿿")
    latin = sum(1 for c in t if c.isascii() and c.isalpha())

    if not declared:
        # 선언이 없으면 문자 구성으로 추론한다(약한 근거라도 쓴다)
        if hangul:
            return "ko"
        if kana:
            return "ja"
        if han:
            return "zh"
        if latin >= 3:
            return "en"
        return None

    # 선언이 있을 때는 입력이 선언과 분명히 다른 문자일 때만 바꾼다
    if hangul >= 2 and declared != "ko":
        return "ko"
    if declared == "ko" and hangul == 0:
        if kana >= 2:
            return "ja"
        if han >= 2:
            return "zh"
        if latin >= 8:
            return "en"
    if declared in ("en", "zh") and kana >= 2 and hangul == 0:
        return "ja"
    if declared in ("en", "ja") and han >= 2 and kana == 0 and hangul == 0:
        return "zh"
    if declared in ("zh", "ja") and hangul == 0 and kana == 0 and han == 0 and latin >= 8:
        return "en"
    return declared


def _prepend_language(chat_history: list, language: str | None) -> list:
    """감지된 언어 코드가 있으면 히스토리 맨 앞에 기본 언어 SystemMessage를 주입."""
    if not language:
        return chat_history
    normalized = language if language in _NATIVE_LANGS else "en"
    instruction = _LANG_INSTRUCTIONS.get(normalized)
    if not instruction:
        return chat_history
    return [SystemMessage(content=instruction)] + chat_history


# 화면별 가능 동작 짧은 안내 (프롬프트 [화면별 가능 동작] 과 일치시켜 유지)
_SCREEN_HINT: dict[str, str] = {
    "start": "navigate('orderType')로 주문 시작, set_language/set_gesture/set_camera 가능.",
    "orderType": "ui_action order_type(dine-in|takeout)로 매장/포장 선택.",
    "menu": "add_item으로 담기, ui_action select_category/menu_page/open_item, navigate('cart').",
    "cart": "update_qty/remove_item/clear_cart, ui_action start_checkout/points/points_phone/payment_method.",
    "complete": "navigate('start')로 새 주문.",
}

# 화면에 실제로 무엇이 보이는지 설명하는 문장 — 시각장애인이 "이 화면 뭐야", "읽어줘" 처럼
# 물었을 때 그대로 읽어줄 수 있도록 화면 구성요소를 서술한다. (메뉴/장바구니 내용 자체는
# 각각 list_menu/search_menu 호출 결과나 아래 _cart_summary로 별도 제공됨 — 여기서는
# 레이아웃/버튼 설명만 담당)
_SCREEN_DESCRIPTION: dict[str, str] = {
    "start": "대기 화면입니다. 중앙에 로고와 배경 사진이 있고, 화면 하단에 '주문 시작하기' 버튼, "
             "우측 상단에 작은 '회원가입' 버튼이 있습니다.",
    "orderType": "매장 식사 또는 포장을 선택하는 화면입니다. 화면에 두 개의 큰 카드가 나란히 있고, "
                 "왼쪽 카드가 매장 식사, 오른쪽 카드가 포장입니다.",
    "menu": "메뉴를 고르는 화면입니다. 상단에 추천메뉴/버거/사이드/음료 탭이 있고, "
            "선택한 탭의 메뉴들이 사진, 이름, 가격과 함께 목록으로 나열되어 있습니다. "
            "구체적인 메뉴 이름과 가격은 list_menu 또는 search_menu 도구로 조회해서 안내한다.",
    "cart": "장바구니 화면입니다. 담긴 메뉴 목록과 각 줄의 수량·가격, 합계 금액이 보이고, "
            "화면 하단에 '결제하기' 버튼이 있습니다. 담긴 항목은 아래 장바구니 요약을 그대로 읽어준다.",
    "complete": "주문이 완료된 화면입니다. 화면 중앙에 주문번호가 크게 표시되고, "
                "잠시 후 자동으로 처음 화면으로 돌아갑니다.",
}


def _context_message(cart: list, screen: str | None, order_type: str | None = None,
                     modal_state: dict | None = None) -> str:
    """현재 화면 + 주문 유형 + 가능 동작 + 장바구니 요약을 합친 컨텍스트 메시지."""
    parts: list[str] = []
    if screen:
        hint = _SCREEN_HINT.get(screen, "")
        parts.append(f"현재 화면: {screen}" + (f" — 가능 동작: {hint}" if hint else ""))
        desc = _SCREEN_DESCRIPTION.get(screen, "")
        if desc:
            parts.append(f"화면 구성: {desc}")
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
    fixed_input = fix_stt(user_input)   # 알려진 STT 오인식(예: "내장에서" → "매장에서") 교정
    set_stt_original(user_input if fixed_input != user_input else "")
    user_input = fixed_input
    set_user_input(user_input)
    snapshot_before = checkout_snapshot(session_id)   # 이 턴이 시작되기 전 결제 진행 상태
    set_checkout_snapshot(snapshot_before)
    reset_actions()
    reset_guards()
    set_last_bot_text("")
    set_recent_user_text("")
    language = _resolve_language(language, user_input)   # 입력 문자와 선언 언어가 다르면 입력 쪽을 따른다

    # 배경 소리·음악이 말로 인식된 것으로 보이면 LLM을 부르지 않고 다시 말해 달라고 한다(비용도 절약)
    if guard_mode() != "off" and is_noise(user_input):
        enforcing = guard_mode() == "enforce"
        record_guard("noise", f"「{user_input[:30]}」 도메인 어휘 없음", blocked=enforcing)
        if enforcing:
            output = NOISE_REPLY.get(language if language in NOISE_REPLY else "ko", NOISE_REPLY["ko"])
            log_turn(
                session_id=session_id, user_input=user_input, output=output, actions=[],
                language=language, screen=screen, order_type=order_type,
            )
            yield f"data: {json.dumps({'done': True, 'output': output, 'guards': get_guard_hits()}, ensure_ascii=False)}\n\n"
            return

    if is_cart_status_query(user_input):
        output = format_cart_status_reply(cart, language, user_input)
        try:
            memory = await get_memory(session_id)
            await save_and_prune(memory, user_input, output)
        except Exception:  # noqa: BLE001 - cart status must not depend on memory/model health
            pass
        log_turn(
            session_id=session_id, user_input=user_input, output=output, actions=[],
            language=language, screen=screen, order_type=order_type,
        )
        yield f"data: {json.dumps({'done': True, 'output': output, 'guards': get_guard_hits()}, ensure_ascii=False)}\n\n"
        return

    output_parts: list[str] = []
    in_tool_call = False
    emitted_count = 0  # 이미 인라인으로 전송한 액션 수 추적
    memory = None

    # ★ 메모리 로드/에이전트 생성부터 astream_events까지 전부 한 try 안에 둔다. 이전에는
    # astream_events 루프만 감쌌는데, get_memory/aload_memory_variables 쪽에서 예외가 나면
    # 첫 yield 전에 함수가 그냥 죽어버려 프론트가 "서버와 연결이 잠시 어려워요" 오류를 보게
    # 됐다 — 실제로 재현된 문제. 어디서 실패하든 항상 done 이벤트로 마무리한다.
    stream_error: Exception | None = None
    try:
        memory = await get_memory(session_id)
        executor = get_agent_executor()

        mem_vars = await memory.aload_memory_variables({})
        chat_history = _prepend_language(
            mem_vars.get("chat_history", []), language
        )
        _remember_history(mem_vars)

        # 현재 화면 + 주문 유형 + 팝업 상태 + 장바구니 요약을 chat_history 앞에 SystemMessage 로 주입
        discount_context = await get_active_discount_context()
        context = _context_message(cart, screen, order_type, modal_state)
        chat_history = [SystemMessage(content=f"{context}\n\n{discount_context}")] + chat_history

        async for event in executor.astream_events(
            {"input": _agent_input(user_input, language, modal_state), "chat_history": chat_history},
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
    except Exception as e:  # noqa: BLE001
        stream_error = e

    output = "".join(output_parts)
    if output.startswith("Agent stopped"):   # 반복 한도 초과 — 내부 메시지를 손님에게 노출하지 않는다
        output = _fallback_message(language)

    if stream_error is not None:
        if not output:
            output = _fallback_message(language)
        log_turn(
            session_id=session_id, user_input=user_input, output=output, actions=get_actions(),
            language=language, screen=screen, order_type=order_type, error=str(stream_error),
        )
        # 이번 턴 저장은 건너뛴다 — 부분 응답을 히스토리에 남기면 다음 턴이 더 헷갈릴 수 있다.
        yield f"data: {json.dumps({'done': True, 'output': output, 'guards': get_guard_hits()}, ensure_ascii=False)}\n\n"
        return

    # LLM이 말로만 처리하고 도구를 빼먹은 핵심 동작(주문 유형·결제 시작·결제 수단)을 규칙으로 보완
    ensure_actions(session_id, user_input, screen, cart, snapshot_before)
    output = _align_reply_with_actions(output)
    await save_and_prune(memory, user_input, output)

    # 인라인으로 아직 전송되지 않은 나머지 액션 전송 (안전장치)
    remaining = get_actions()[emitted_count:]
    for action in remaining:
        yield f"data: {json.dumps({'action': action}, ensure_ascii=False)}\n\n"

    log_turn(
        session_id=session_id, user_input=user_input, output=output, actions=get_actions(),
        language=language, screen=screen, order_type=order_type,
    )
    yield f"data: {json.dumps({'done': True, 'output': output, 'guards': get_guard_hits()}, ensure_ascii=False)}\n\n"


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
    fixed_input = fix_stt(user_input)   # 알려진 STT 오인식(예: "내장에서" → "매장에서") 교정
    set_stt_original(user_input if fixed_input != user_input else "")
    user_input = fixed_input
    set_user_input(user_input)
    snapshot_before = checkout_snapshot(session_id)   # 이 턴이 시작되기 전 결제 진행 상태
    set_checkout_snapshot(snapshot_before)
    reset_actions()
    reset_guards()
    set_last_bot_text("")
    set_recent_user_text("")
    language = _resolve_language(language, user_input)   # 입력 문자와 선언 언어가 다르면 입력 쪽을 따른다

    # 배경 소리·음악이 말로 인식된 것으로 보이면 LLM을 부르지 않고 다시 말해 달라고 한다(비용도 절약)
    if guard_mode() != "off" and is_noise(user_input):
        enforcing = guard_mode() == "enforce"
        record_guard("noise", f"「{user_input[:30]}」 도메인 어휘 없음", blocked=enforcing)
        if enforcing:
            output = NOISE_REPLY.get(language if language in NOISE_REPLY else "ko", NOISE_REPLY["ko"])
            log_turn(
                session_id=session_id, user_input=user_input, output=output, actions=[],
                language=language, screen=screen, order_type=order_type,
            )
            return {"session_id": session_id, "output": output, "actions": [], "intermediate_steps": [],
                    "guards": get_guard_hits()}

    if is_cart_status_query(user_input):
        output = format_cart_status_reply(cart, language, user_input)
        try:
            memory = await get_memory(session_id)
            await save_and_prune(memory, user_input, output)
        except Exception:  # noqa: BLE001 - cart status must not depend on memory/model health
            pass
        log_turn(
            session_id=session_id, user_input=user_input, output=output, actions=[],
            language=language, screen=screen, order_type=order_type,
        )
        return {
            "session_id": session_id,
            "output": output,
            "actions": [],
            "intermediate_steps": [],
        }

    memory = await get_memory(session_id)
    executor = get_agent_executor()

    mem_vars = await memory.aload_memory_variables({})
    chat_history = _prepend_language(
        mem_vars.get("chat_history", []), language
    )
    _remember_history(mem_vars)

    discount_context = await get_active_discount_context()
    context = _context_message(cart, screen, order_type, modal_state)
    chat_history = [SystemMessage(content=f"{context}\n\n{discount_context}")] + chat_history

    result = await executor.ainvoke(
        {"input": _agent_input(user_input, language, modal_state), "chat_history": chat_history}
    )
    output = result.get("output", "")
    if output.startswith("Agent stopped"):   # 반복 한도 초과 — 내부 메시지를 손님에게 노출하지 않는다
        output = _fallback_message(language)

    # LLM이 말로만 처리하고 도구를 빼먹은 핵심 동작을 규칙으로 보완
    ensure_actions(session_id, user_input, screen, cart, snapshot_before)
    output = _align_reply_with_actions(output)

    await save_and_prune(memory, user_input, output)
    log_turn(
        session_id=session_id, user_input=user_input, output=output, actions=get_actions(),
        language=language, screen=screen, order_type=order_type,
    )

    return {
        "session_id": session_id,
        "output": output,
        "actions": get_actions(),
        "guards": get_guard_hits(),
        "intermediate_steps": [
            {
                "tool": getattr(step[0], "tool", str(step[0])),
                "tool_input": getattr(step[0], "tool_input", None),
                "result": step[1],
            }
            for step in result.get("intermediate_steps", [])
        ],
    }
