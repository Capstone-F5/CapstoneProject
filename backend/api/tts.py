"""
TTS 엔드포인트.

POST /ai_modules/tts
- Body: { "text": "...", "voice": "alloy" }
- StreamingResponse 로 mp3 청크 즉시 전송 (응답 지연 2초 이내 목표).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.tts_service import stream_tts


router = APIRouter(prefix="/ai_modules", tags=["tts"])


_MIME_BY_FORMAT = {
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "flac": "audio/flac",
}


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str | None = None
    format: str = "mp3"


@router.post("/tts")
async def tts(req: TTSRequest):
    if req.format not in _MIME_BY_FORMAT:
        raise HTTPException(400, f"지원하지 않는 format: {req.format}")

    try:
        gen = stream_tts(req.text, voice=req.voice, audio_format=req.format)
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    return StreamingResponse(
        gen,
        media_type=_MIME_BY_FORMAT[req.format],
        headers={"Cache-Control": "no-store"},
    )
