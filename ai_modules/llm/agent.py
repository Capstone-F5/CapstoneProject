"""
OpenAI Function Calling 기반 LangChain Agent 빌더.
"""
from __future__ import annotations

import os

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from .prompts import SYSTEM_PROMPT
from .tools import TOOLS


def build_agent_executor() -> AgentExecutor:
    """매 요청마다 새로 만들기에는 무거우니, 모듈 로더에서 1회 빌드해 재사용."""
    model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(
        model=model,
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm=llm, tools=TOOLS, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=6,
        return_intermediate_steps=True,
    )


_executor: AgentExecutor | None = None


def get_agent_executor() -> AgentExecutor:
    global _executor
    if _executor is None:
        _executor = build_agent_executor()
    return _executor
