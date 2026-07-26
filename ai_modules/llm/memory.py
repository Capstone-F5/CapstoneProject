"""
세션별 ConversationSummaryBufferMemory 관리.

- 메모리는 LangChain legacy 인터페이스(0.2+ 에서 deprecated 지만 동작) 사용.
- 토큰 한도(기본 800) 초과 시 자동 요약하여 컨텍스트 길이 제어.

★ 주의: ConversationSummaryBufferMemory는 동기 save_context()에만 prune()(요약/축소) 로직을
  넣어두고, 비동기 asave_context()는 이를 전혀 호출하지 않는다(LangChain 0.2.x의 구조적 함정).
  이 프로젝트는 전부 asave_context()로 호출하므로, save_and_prune()에서 직접 prune()을
  이어서 호출해 준다. 이걸 빠뜨리면 대화가 길어질수록 히스토리가 전혀 요약되지 않고 무한히
  쌓여, 결국 토큰/속도 제한에 걸려 LLM 응답이 끊기는 문제가 재현된다.
"""
from __future__ import annotations

import asyncio
import logging
import os

from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


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


async def save_and_prune(
    memory: ConversationSummaryBufferMemory, user_input: str, output: str
) -> None:
    """asave_context 후 누락된 prune()을 직접 호출해 히스토리 요약/축소를 보장한다.

    prune()은 한도 초과 시 동기 LLM 호출(self.llm.predict)을 하므로 스레드로 넘겨
    이벤트 루프를 막지 않는다. 요약 호출 자체가 실패해도(네트워크/속도 제한 등) 이번 턴의
    응답은 이미 사용자에게 전달된 뒤이므로, 예외를 삼키고 다음 턴에 다시 시도한다.
    """
    await memory.asave_context({"input": user_input}, {"output": output})
    try:
        await asyncio.to_thread(memory.prune)
    except Exception:  # noqa: BLE001
        logger.warning("memory.prune() 실패 — 히스토리 요약 없이 다음 턴에 재시도", exc_info=True)
