"""
LangChain Agent 실행 래퍼.

- 요청 단위로 session_id ContextVar 를 세팅 → tools 가 같은 세션의 장바구니를 조작.
- ConversationSummaryBufferMemory 로 대화 맥락 유지.
"""
from __future__ import annotations

from typing import Any

from ai_modules.llm.agent import get_agent_executor
from ai_modules.llm.memory import get_memory
from ai_modules.llm.session_context import set_session_id


async def run_agent(session_id: str, user_input: str) -> dict[str, Any]:
    set_session_id(session_id)

    memory = await get_memory(session_id)
    executor = get_agent_executor()

    mem_vars = await memory.aload_memory_variables({})
    chat_history = mem_vars.get("chat_history", [])

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
