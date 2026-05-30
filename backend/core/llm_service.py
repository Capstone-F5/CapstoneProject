"""
LangChain Agent 실행 래퍼.

- 요청 단위로 session_id ContextVar 를 세팅 → tools 가 같은 세션의 장바구니를 조작.
- ConversationSummaryBufferMemory 로 대화 맥락 유지.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from langchain_core.messages import SystemMessage

from ai_modules.llm.agent import get_agent_executor
from ai_modules.llm.memory import get_memory
from ai_modules.llm.session_context import set_session_id

# 첫 발화에서 감지된 언어를 LLM에 강제 지시하는 SystemMessage 텍스트
_LANG_INSTRUCTIONS: dict[str, str] = {
    "ko": "이 대화에서는 반드시 한국어로만 답변하세요.",
    "en": "In this conversation, you must respond in English only.",
    "zh": "在这次对话中，请务必只用中文回答。",
    "ja": "この会話では、必ず日本語のみで答えてください。",
}
# ko / zh / ja 외 모든 언어는 영어로 처리
_NATIVE_LANGS = frozenset({"ko", "zh", "ja"})


def _prepend_language(chat_history: list, language: str | None) -> list:
    """감지된 언어 코드가 있으면 히스토리 맨 앞에 언어 고정 SystemMessage를 주입.
    ko/zh/ja 외 언어는 영어로 fallback."""
    if not language:
        return chat_history
    normalized = language if language in _NATIVE_LANGS else "en"
    instruction = _LANG_INSTRUCTIONS.get(normalized)
    if not instruction:
        return chat_history
    return [SystemMessage(content=instruction)] + chat_history


async def run_agent_stream(
    session_id: str,
    user_input: str,
    language: str | None = None,
) -> AsyncIterator[str]:
    """LLM 응답을 SSE(text/event-stream) 형식으로 토큰 단위 yield.

    최종 답변 토큰만 스트리밍(툴 호출 중 LLM 출력은 제외).
    마지막에 data: {"done": true, "output": "..."} 전송.
    """
    set_session_id(session_id)
    memory = await get_memory(session_id)
    executor = get_agent_executor()

    mem_vars = await memory.aload_memory_variables({})
    chat_history = _prepend_language(
        mem_vars.get("chat_history", []), language
    )

    output_parts: list[str] = []
    in_tool_call = False

    async for event in executor.astream_events(
        {"input": user_input, "chat_history": chat_history},
        version="v1",
    ):
        kind = event["event"]

        if kind == "on_tool_start":
            in_tool_call = True

        elif kind == "on_tool_end":
            in_tool_call = False

        elif kind == "on_chat_model_stream" and not in_tool_call:
            chunk = event["data"]["chunk"]
            content: str = getattr(chunk, "content", "") or ""
            tool_calls = getattr(chunk, "additional_kwargs", {}).get("tool_calls")
            if content and not tool_calls:
                output_parts.append(content)
                yield f"data: {json.dumps({'token': content}, ensure_ascii=False)}\n\n"

    output = "".join(output_parts)
    await memory.asave_context({"input": user_input}, {"output": output})
    yield f"data: {json.dumps({'done': True, 'output': output}, ensure_ascii=False)}\n\n"


async def run_agent(
    session_id: str,
    user_input: str,
    language: str | None = None,
) -> dict[str, Any]:
    set_session_id(session_id)

    memory = await get_memory(session_id)
    executor = get_agent_executor()

    mem_vars = await memory.aload_memory_variables({})
    chat_history = _prepend_language(
        mem_vars.get("chat_history", []), language
    )

    result = await executor.ainvoke(
        {"input": user_input, "chat_history": chat_history}
    )
    output = result.get("output", "")

    # 메모리에 이번 턴 저장
    await memory.asave_context({"input": user_input}, {"output": output})

    return {
        "session_id": session_id,
        "output": output,
        "intermediate_steps": [
            {
                "tool": getattr(step[0], "tool", str(step[0])),
                "tool_input": getattr(step[0], "tool_input", None),
                "result": step[1],
            }
            for step in result.get("intermediate_steps", [])
        ],
    }
