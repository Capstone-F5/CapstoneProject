"""
OpenAI Whisper STT 비동기 래퍼.

- Zero-shot 자동 언어 감지: language 파라미터 미지정.
- response_format="verbose_json" → 감지된 언어(detected_language) 반환.
- AsyncOpenAI 클라이언트 사용해 FastAPI 이벤트 루프를 막지 않음.
"""
from __future__ import annotations

import io
import os
from typing import Any

from openai import AsyncOpenAI


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def transcribe_bytes(
    audio_bytes: bytes,
    filename: str = "audio.webm",
) -> dict[str, Any]:
    """
    오디오 바이트 → Whisper 전사.

    Returns:
        { "text": str, "language": str, "duration": float | None }
    """
    model = os.getenv("OPENAI_STT_MODEL", "whisper-1")
    client = _get_client()

    buf = io.BytesIO(audio_bytes)
    buf.name = filename  # openai SDK 가 확장자로 mime 추론

    resp = await client.audio.transcriptions.create(
        model=model,
        file=buf,
        response_format="verbose_json",  # 감지된 언어 반환
    )

    return {
        "text": (resp.text or "").strip(),
        "language": getattr(resp, "language", None),
        "duration": getattr(resp, "duration", None),
    }
