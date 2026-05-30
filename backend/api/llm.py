"""
LLM Agent 엔드포인트.

POST /ai_modules/llm
- Body: { "session_id": "...", "input": "...텍스트 (STT 결과)..." }
- 응답: { "output": "...에이전트 답변...", "intermediate_steps": [...tool 호출 내역...] }
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.llm_service import run_agent, run_agent_stream
from ai_modules.llm.memory import reset_memory


router = APIRouter(prefix="/ai_modules", tags=["llm"])


class LLMRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    input: str = Field(..., min_length=1, max_length=4000)
    language: str | None = Field(None, max_length=10)  # STT 감지 언어 코드 (ko/en/zh/ja)


@router.post("/llm")
async def llm(req: LLMRequest):
    try:
        return await run_agent(req.session_id, req.input, language=req.language)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"LLM 처리 실패: {e}")


@router.post("/llm/stream")
async def llm_stream(req: LLMRequest):
    """SSE 스트리밍 엔드포인트 — 토큰 단위로 text/event-stream 반환."""
    try:
        return StreamingResponse(
            run_agent_stream(req.session_id, req.input, language=req.language),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"LLM 스트리밍 실패: {e}")


@router.post("/llm/reset")
async def llm_reset(session_id: str):
    await reset_memory(session_id)
    return {"ok": True, "session_id": session_id}
