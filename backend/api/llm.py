"""
LLM Agent 엔드포인트.

POST /ai_modules/llm
- Body: { "session_id": "...", "input": "...텍스트 (STT 결과)...", "cart": [...], "screen": "..." }
- 응답: { "output": "...", "actions": [...], "intermediate_steps": [...] }

POST /ai_modules/llm/stream
- SSE: data:{"token":"..."} ... data:{"action":{...}} ... data:{"done":true,"output":"..."}

POST /ai_modules/llm/note
- 프론트가 LLM 없이 규칙 기반으로 처리한 짧은 응답("네"/"아니요")을 대화 기록에만 남긴다.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.cart_context import cart_lines_from_db
from ai_modules.llm.memory import get_memory, reset_memory, save_and_prune
from core.db import SessionLocal
from core.llm_service import run_agent, run_agent_stream
from dao import cart_dao


router = APIRouter(prefix="/ai_modules", tags=["llm"])


async def _authoritative_cart(session_id: str, fallback: list[dict]) -> list[dict]:
    """LLM 컨텍스트는 DB 카트를 우선 사용하고, 아직 행이 없으면 요청 스냅샷을 쓴다.

    터치 담기 직후에는 브라우저 상태와 DB 커밋 사이에 짧은 시차가 생길 수 있다.
    같은 요청에서 전달된 스냅샷을 폴백으로 사용해 장바구니가 비었다고 잘못 안내하지 않는다.
    """
    fallback = fallback or []
    try:
        async with SessionLocal() as db:
            cart = await cart_dao.get_cart_with_items(db, session_id)
            return cart_lines_from_db(cart, fallback)
    except Exception:
        # DB가 일시적으로 읽히지 않는 경우에는 기존 클라이언트 스냅샷으로 계속 처리한다.
        return fallback


class CartLine(BaseModel):
    cart_item_id: str | float | int | None = None
    # Accept older clients until every kiosk has sent the normalized field.
    cart_id: str | float | int | None = None
    menu_id: str | int
    name: str | None = None
    item_type: str = "single"
    quantity: int = 1
    unit_price: float = 0
    exclusion: str = "없음"
    exclusions: list[str] = Field(default_factory=list)
    side: str | None = None
    drink: str | None = None
    special_note: str | None = None


class ModalState(BaseModel):
    menu_id:   str | int
    name:      str | None = None
    item_type: str = "single"
    qty:       int = 1
    exclusion: str | None = None
    side:      str | None = None
    drink:     str | None = None

class LLMRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    input: str = Field(..., min_length=1, max_length=4000)
    language: str | None = Field(None, max_length=10)  # STT 감지 언어 코드 (ko/en/zh/ja)
    screen: str | None = None           # 현재 화면 (menu/cart 등)
    order_type: str | None = None       # 매장/포장 선택 여부 (dine-in|takeout|None)
    cart: list[CartLine] = []           # 현재 장바구니 스냅샷
    modal_state: ModalState | None = None  # 현재 열린 팝업 선택 상태


@router.post("/llm")
async def llm(req: LLMRequest):
    try:
        cart_dicts = await _authoritative_cart(req.session_id, [c.model_dump() for c in req.cart])
        return await run_agent(
            req.session_id,
            req.input,
            language=req.language,
            cart=cart_dicts,
            screen=req.screen,
            order_type=req.order_type,
            modal_state=req.modal_state.model_dump() if req.modal_state else None,
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"LLM 처리 실패: {e}")


@router.post("/llm/stream")
async def llm_stream(req: LLMRequest):
    """SSE 스트리밍 엔드포인트 — 토큰 단위로 text/event-stream 반환."""
    try:
        cart_dicts = await _authoritative_cart(req.session_id, [c.model_dump() for c in req.cart])
        return StreamingResponse(
            run_agent_stream(
                req.session_id,
                req.input,
                language=req.language,
                cart=cart_dicts,
                modal_state=req.modal_state.model_dump() if req.modal_state else None,
                screen=req.screen,
                order_type=req.order_type,
            ),
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


class QuickReplyNote(BaseModel):
    session_id: str
    user_text: str = Field(..., max_length=200)
    note: str = Field(..., max_length=300)


@router.post("/llm/note", status_code=204)
async def llm_note(body: QuickReplyNote):
    """규칙 기반 빠른 응답을 LLM 대화 기록에 남긴다(LLM 호출 없음).

    빠른 경로는 LLM을 거치지 않으므로 그대로 두면 이후 턴에서 LLM이 같은 질문을 다시 하거나
    사용자의 답을 모르는 채 대화를 이어간다. 사용자 발화와 화면이 처리한 결과를 한 턴으로 저장한다.
    기록 실패가 사용자 흐름을 막으면 안 되므로 예외는 삼킨다.
    """
    try:
        memory = await get_memory(body.session_id)
        await save_and_prune(memory, body.user_text, body.note)
    except Exception:  # noqa: BLE001
        pass
