"""
세션별 ConversationSummaryBufferMemory 관리.

- 메모리는 LangChain legacy 인터페이스(0.2+ 에서 deprecated 지만 동작) 사용.
- 토큰 한도(기본 800) 초과 시 자동 요약하여 컨텍스트 길이 제어.
"""
from __future__ import annotations

import asyncio
import os

from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI


_memories: dict[str, ConversationSummaryBufferMemory] = {}
_lock = asyncio.Lock()


def _make_memory() -> ConversationSummaryBufferMemory:
    model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    summary_llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    return ConversationSummaryBufferMemory(
        llm=summary_llm,
        max_token_limit=800,
        memory_key="chat_history",
        return_messages=True,
        input_key="input",
        output_key="output",
    )


async def get_memory(session_id: str) -> ConversationSummaryBufferMemory:
    async with _lock:
        mem = _memories.get(session_id)
        if mem is None:
            mem = _make_memory()
            _memories[session_id] = mem
        return mem


async def reset_memory(session_id: str) -> None:
    async with _lock:
        _memories.pop(session_id, None)
