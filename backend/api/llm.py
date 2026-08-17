"""
LLM Agent 엔드포인트.

POST /ai_modules/llm
- Body: { "session_id": "...", "input": "...텍스트 (STT 결과)...", "cart": [...], "screen": "..." }
- 응답: { "output": "...", "actions": [...], "intermediate_steps": [...] }

POST /ai_modules/llm/stream
- SSE: data:{"token":"..."} ... data:{"action":{...}} ... data:{"done":true,"output":"..."}
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_modules.llm.memory import reset_memory
from core.db import SessionLocal
from core.llm_service import run_agent, run_agent_stream
from dao import cart_dao


router = APIRouter(prefix="/ai_modules", tags=["llm"])


async def _authoritative_cart(session_id: str, fallback: list[dict]) -> list[dict]:
    """LLM 컨텍스트는 React state가 아닌 DB 장바구니를 최우선으로 사용한다.

    터치 담기 직후에는 브라우저의 cart state가 아직 재렌더되지 않을 수 있다. 이때
    빈 스냅샷을 그대로 LLM에 넘기면 실제로 담긴 메뉴가 없다고 잘못 안내할 수 있다.
    """
    try:
        async with SessionLocal() as db:
            cart = await cart_dao.get_cart_with_items(db, session_id)
            if cart is None:
                return []
            return [
                {
                    "cart_id": item.id,
                    "menu_id": item.menu_item_id,
                    "name": item.menu_item.name_ko if item.menu_item else None,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "item_type": "single",
                    "exclusion": item.special_note or "없음",
                }
                for item in cart.items
            ]
    except Exception:
        # DB가 일시적으로 읽히지 않는 경우에는 기존 클라이언트 스냅샷으로 계속 처리한다.
        return fallback


class CartLine(BaseModel):
    cart_id: str | float | int | None = None
    menu_id: str | int
    name: str | None = None
    item_type: str = "single"
    quantity: int = 1
    unit_price: float = 0
    exclusion: str = "없음"
    side: str | None = None
    drink: str | None = None


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
