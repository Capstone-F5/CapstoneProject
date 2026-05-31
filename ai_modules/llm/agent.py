"""
OpenAI Function Calling 기반 LangChain Agent 빌더.
MVP: ACTION_TOOLS (액션 발행 전용) 사용. tools.py 는 Phase 5 에서 복원.
"""
from __future__ import annotations

import os

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from .action_tools import ACTION_TOOLS
from .menu_catalog import render_catalog_for_prompt
from .prompts import SYSTEM_PROMPT_TEMPLATE


def build_agent_executor() -> AgentExecutor:
    """싱글톤 빌드 시 1회 실행. 카탈로그를 시스템 프롬프트에 합성."""
    model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(
        model=model,
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(catalog=render_catalog_for_prompt())

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm=llm, tools=ACTION_TOOLS, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=ACTION_TOOLS,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=8,
        return_intermediate_steps=True,
    )


_executor: AgentExecutor | None = None


def get_agent_executor() -> AgentExecutor:
    global _executor
    if _executor is None:
        _executor = build_agent_executor()
    return _executor
