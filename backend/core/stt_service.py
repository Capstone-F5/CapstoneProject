"""
OpenAI STT 비동기 래퍼.

- gpt-4o-mini-transcribe / gpt-4o-transcribe / whisper-1 모두 지원.
- verbose_json 우선 시도 → 미지원 모델은 json 포맷으로 폴백.
- 메뉴 어휘 힌트(prompt)로 고유명사 전사 정확도 향상.
"""
from __future__ import annotations

import io
import logging
import os
from typing import Any

from openai import AsyncOpenAI

from ai_modules.llm.menu_catalog import (
    MENU_CATALOG,
    SET_DRINKS,
    SET_SIDES,
    render_vocab_for_stt,
)

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None

# 메뉴 어휘 힌트 — 모듈 로드 시 1회 생성(정적)
_STT_PROMPT = render_vocab_for_stt()

# 프롬프트 에코 감지용: 카탈로그에 등장하는 모든 메뉴/옵션 이름
_VOCAB_NAMES = (
    [m["name"] for m in MENU_CATALOG]
    + [s["name"] for s in SET_SIDES]
    + [d["name"] for d in SET_DRINKS]
)


def _is_prompt_echo(text: str) -> bool:
    """Whisper가 무음/잡음 입력에 prompt(메뉴 어휘 힌트)를 그대로 토해낸 경우 감지.

    실제 손님은 메뉴명을 5개 이상 카탈로그 순서대로 나열하지 않으므로,
    어휘 힌트 고유 표현이나 다수 메뉴명 동시 등장을 에코로 판단한다.
    """
    if not text:
        return False
    # 1) 어휘 힌트 고유 서명 문구
    if "키오스크" in text and "메뉴" in text:
        return True
    # 2) 카탈로그 메뉴명이 5개 이상 한꺼번에 등장
    hit = sum(1 for name in _VOCAB_NAMES if name in text)
    if hit >= 5:
        return True
    # 3) 긴 텍스트가 프롬프트의 부분 문자열 (공백 제거 비교)
    if len(text) > 20:
        norm = text.replace(" ", "")
        if norm and norm in _STT_PROMPT.replace(" ", ""):
            return True
    return False


def _detect_language(text: str) -> str | None:
    """전사 텍스트의 문자 구성으로 언어 추론.

    gpt-4o-mini-transcribe 등 language 필드를 반환하지 않는 모델용.
    지원: ko / ja / zh / en
    """
    if not text:
        return None
    total = len(text.replace(" ", "")) or 1
    korean  = sum(1 for c in text if "가" <= c <= "힣")
    hiragana = sum(1 for c in text if "぀" <= c <= "ヿ")
    cjk     = sum(1 for c in text if "一" <= c <= "鿿")
    latin   = sum(1 for c in text if c.isascii() and c.isalpha())

    if korean / total > 0.15:
        return "ko"
    if hiragana / total > 0.10:
        return "ja"
    if cjk / total > 0.15:
        return "zh"
    if latin / total > 0.25:
        return "en"
    # 짧은 발화나 숫자 위주면 기본 한국어
    return "ko"


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
    오디오 바이트 → STT 전사.

    Returns:
        { "text": str, "language": str | None, "duration": float | None }
    """
    model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    client = _get_client()

    buf = io.BytesIO(audio_bytes)
    buf.name = filename  # SDK가 확장자로 mime 추론

    # whisper-1은 verbose_json으로 언어 감지.
    # 신규 모델(gpt-4o-*-transcribe)은 json/text만 지원 → 텍스트 문자 기반 언어 추론.
    use_verbose = model == "whisper-1"

    resp = await client.audio.transcriptions.create(
        model=model,
        file=buf,
        response_format="verbose_json" if use_verbose else "json",
        prompt=_STT_PROMPT,
    )
    text = (getattr(resp, "text", None) or "").strip()

    # 무음/잡음에 prompt를 그대로 받아쓴 환각이면 빈 텍스트로 처리 → 프론트에서 무시됨
    if _is_prompt_echo(text):
        logger.info("STT prompt echo 감지 → 무시: %s", text[:40])
        text = ""

    if use_verbose:
        language = getattr(resp, "language", None)
    else:
        language = _detect_language(text)

    return {
        "text": text,
        "language": language,
        "duration": getattr(resp, "duration", None) if use_verbose else None,
    }
