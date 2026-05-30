"""
OpenAI TTS 비동기 스트리밍 래퍼.

- async generator 가 mp3 청크를 yield → StreamingResponse 에 연결.
- 첫 청크 즉시 전송으로 체감 지연 최소화.
"""
from __future__ import annotations

import os
from typing import AsyncIterator

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


async def stream_tts(
    text: str,
    voice: str | None = None,
    audio_format: str = "mp3",
) -> AsyncIterator[bytes]:
    """
    OpenAI TTS 응답을 청크 단위로 yield.

    Args:
        text: 합성할 텍스트
        voice: alloy / echo / fable / onyx / nova / shimmer
        audio_format: mp3 / opus / aac / flac
    """
    model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
    voice = voice or os.getenv("OPENAI_TTS_VOICE", "alloy")
    client = _get_client()

    async with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        response_format=audio_format,
    ) as resp:
        async for chunk in resp.iter_bytes(chunk_size=4096):
            if chunk:
                yield chunk
