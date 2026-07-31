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


_TTS_LANG_NAMES: dict[str, str] = {
    "ko": "Korean",
    "ja": "Japanese",
    "zh": "Chinese",
    "en": "English",
}


async def stream_tts(
    text: str,
    voice: str | None = None,
    audio_format: str = "mp3",
    language: str | None = None,
) -> AsyncIterator[bytes]:
    """
    OpenAI TTS 응답을 청크 단위로 yield.

    Args:
        text: 합성할 텍스트
        voice: alloy / echo / fable / onyx / nova / shimmer
        audio_format: mp3 / opus / aac / flac
        language: 현재 언어(ko/ja/zh/en). gpt-4o-mini-tts 이상에서 instructions 생성에 사용.
    """
    model = os.getenv("OPENAI_TTS_MODEL", "tts-1")
    voice = voice or os.getenv("OPENAI_TTS_VOICE", "alloy")
    client = _get_client()

    extra_kwargs: dict = {}
    if language and "gpt-4o" in model:
        lang_name = _TTS_LANG_NAMES.get(language, "Korean")
        extra_kwargs["instructions"] = (
            f"Speak in {lang_name} only. "
            f"Do not switch to another language mid-sentence."
        )

    async with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        response_format=audio_format,
        **extra_kwargs,
    ) as resp:
        async for chunk in resp.iter_bytes(chunk_size=4096):
            if chunk:
                yield chunk
