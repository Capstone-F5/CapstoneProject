"""
STT 엔드포인트.

POST /ai_modules/stt
- multipart/form-data 로 오디오 파일 업로드.
- Whisper-1 + Zero-shot 자동 언어 감지.
- 응답 지연 2초 이내를 위해 AsyncOpenAI 로 비동기 호출.
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.stt_service import transcribe_bytes


router = APIRouter(prefix="/ai_modules", tags=["stt"])


@router.post("/stt")
async def stt(audio: UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(400, "오디오 파일이 필요합니다.")

    data = await audio.read()
    if not data:
        raise HTTPException(400, "오디오 파일이 비어 있습니다.")

    try:
        result = await transcribe_bytes(data, filename=audio.filename or "audio.webm")
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:  # noqa: BLE001  — OpenAI 호출 오류 사용자 노출
        raise HTTPException(502, f"STT 변환 실패: {e}")

    return result
