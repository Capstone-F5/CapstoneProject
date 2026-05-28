"""
LLM Agent 엔드포인트.

POST /ai_modules/llm
- Body: { "session_id": "...", "input": "...텍스트 (STT 결과)..." }
- 응답: { "output": "...에이전트 답변...", "intermediate_steps": [...tool 호출 내역...] }
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.llm_service import run_agent
from ai_modules.llm.memory import reset_memory


router = APIRouter(prefix="/ai_modules", tags=["llm"])


class LLMRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    input: str = Field(..., min_length=1, max_length=4000)


@router.post("/llm")
async def llm(req: LLMRequest):
    try:
        return await run_agent(req.session_id, req.input)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"LLM 처리 실패: {e}")


@router.post("/llm/reset")
async def llm_reset(session_id: str):
    await reset_memory(session_id)
    return {"ok": True, "session_id": session_id}
