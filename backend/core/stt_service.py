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
import re
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


# whisper-1이 구간마다 주는 "말이 없을 확률". 2026-10-04 실험: 무음·잡음에서 나온 환각 구간은 0.85~0.97, 실제 말소리는 0.00~0.40
# (짧은 "네"가 언어 자동 감지에서 0.40). 이 값 이상인 구간은 말이 아니라고 보고 버린다. 언어와 무관하게 동작해서 문구 목록이
# 못 막는 새 환각 문장과 영어·일본어·중국어 환각도 걸러 준다. whisper-1 전용(다른 모델은 구간 정보가 없다).
# 합성(잡음 없는) 음성으로 잰 값이라 실제 매장 소음에서는 정상 발화 값이 올라갈 수 있다 — 환경변수로 조정한다.
NO_SPEECH_DROP = float(os.getenv("STT_NO_SPEECH_DROP", "0.7"))

# 유튜브 마무리 멘트 등 무음·잡음에 Whisper가 지어내는 전형적 문장. 공백을 없애고 소문자로 비교한다(띄어쓰기 변형 대응).
_HALLUCINATION_FRAGMENTS: frozenset[str] = frozenset({
    # 한국어
    "시청해주셔서 감사합니다",
    "구독과 좋아요", "좋아요와 구독",
    "다음 영상에서", "다음 영상",
    "한글자막", "자막 제공", "영상을 시청", "이 영상은",
    "mbc 뉴스", "kbs 뉴스", "sbs 뉴스",
    # 영어 — 언어를 정하지 않은 첫 발화에서 무음·잡음에 실제로 나온다("Thank you for watching.", 2026-10-04 실험)
    "thank you for watching", "thanks for watching", "please subscribe", "like and subscribe",
    "amara.org", "subtitles by", "subtitles provided", "transcribed by", "copyright",
    # 일본어·중국어·러시아어
    "ありがとうございました", "ご視聴ありがとう", "チャンネル登録",
    "感谢您的观看", "感谢观看", "请订阅", "点赞订阅", "謝謝觀看", "字幕",
    "благодарю за просмотр", "субтитры",
})
_HALLUCINATION_COMPACT: frozenset[str] = frozenset(re.sub(r"\s+", "", f.lower()) for f in _HALLUCINATION_FRAGMENTS)
# 문장 전체가 이것뿐이면 환각이다(무음에 "you"가 단독으로 나온다). "thank you"처럼 실제 손님이 말할 수 있는 것은 넣지 않는다.
_HALLUCINATION_EXACT: frozenset[str] = frozenset({"you", "bye"})

_COMMON_ENGLISH_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "yes", "no", "hi", "hello", "ok", "okay",
    "please", "want", "i", "me", "you", "we", "my", "your", "to", "and",
})


_PAYMENT_NORMALIZATIONS: list[tuple[str, str]] = [
    # 간편결제 오인식 보정
    ("간편결재", "간편결제"),
    ("간편 결재", "간편결제"),
    ("간편 결제", "간편결제"),
    ("갠편결제", "간편결제"),
    ("갠편 결제", "간편결제"),
    ("간편결체", "간편결제"),
    # 네이버페이
    ("네이버 패이", "네이버페이"),
    ("네이버 페이", "네이버페이"),
    ("내이버페이", "네이버페이"),
    ("네이버빼이", "네이버페이"),
    # 카카오페이
    ("카카오 패이", "카카오페이"),
    ("카카오 페이", "카카오페이"),
    ("가카오페이", "카카오페이"),
    ("카카오빼이", "카카오페이"),
    # 삼성페이
    ("삼성 패이", "삼성페이"),
    ("삼성 페이", "삼성페이"),
    ("삼성빼이", "삼성페이"),
    # 페이코
    ("패이코", "페이코"),
    ("페이 코", "페이코"),
    # 제로페이
    ("제로 패이", "제로페이"),
    ("제로 페이", "제로페이"),
    ("제로빼이", "제로페이"),
    # QR
    # 결제 일반 — "결재할게요", "카드로 결재" 등(위의 "간편결재"류는 앞에서 먼저 처리된다)
    ("결재", "결제"),
    ("큐알코드", "QR코드"),
    ("큐 알", "QR"),
    ("큐알", "QR"),
]


def _normalize_payment_text(text: str) -> str:
    """간편결제 관련 발화의 STT 오인식을 정규화."""
    for wrong, correct in _PAYMENT_NORMALIZATIONS:
        if wrong in text:
            text = text.replace(wrong, correct)
    return text


def _is_hallucination(text: str) -> bool:
    """Whisper 전형적 환각(유튜브 자막 패턴 등) 감지."""
    if not text:
        return False
    t = re.sub(r"\s+", "", text.lower())
    if not re.search(r"[0-9a-z가-힣぀-ヿ一-鿿]", t):
        return True   # "."·"…"처럼 글자가 하나도 없으면 말이 아니다
    if t.strip(".,!?~") in _HALLUCINATION_EXACT:
        return True
    return any(frag in t for frag in _HALLUCINATION_COMPACT)


def _drop_no_speech(segments, threshold: float) -> tuple[str | None, float | None]:
    """구간별 no_speech_prob가 threshold 이상인 구간을 버리고 남은 구간의 텍스트를 이어 돌려준다.
    (남은 텍스트 또는 None, 전체 구간 중 최대 no_speech_prob). 버린 구간이 없거나 구간 정보가 없으면 텍스트는 None —
    호출한 쪽이 원래 텍스트를 그대로 쓴다."""
    probs, kept, dropped = [], [], False
    for seg in segments or []:
        p = getattr(seg, "no_speech_prob", None)
        if p is None and isinstance(seg, dict):
            p = seg.get("no_speech_prob")
        seg_text = getattr(seg, "text", None) if not isinstance(seg, dict) else seg.get("text")
        if p is None:
            kept.append((seg_text or "").strip())
            continue
        probs.append(float(p))
        if float(p) >= threshold:
            dropped = True
        else:
            kept.append((seg_text or "").strip())
    peak = max(probs) if probs else None
    return (" ".join(t for t in kept if t).strip() if dropped else None), peak


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
        # 짧은 텍스트가 전부 Latin이고 일반 영어 단어가 없으면 핀인/로마자 의심 → 불확실 처리
        stripped = text.lower().strip()
        tokens = set(stripped.split())
        if len(stripped) <= 15 and not tokens & _COMMON_ENGLISH_WORDS:
            return None
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


_SUPPORTED_LANGS = {"ko", "en", "ja", "zh"}


async def transcribe_bytes(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
    prompt_override: str | None = None,
) -> dict[str, Any]:
    """
    오디오 바이트 → STT 전사.

    Args:
        language: 이 세션에서 이미 감지되어 고정된 언어(ko/en/ja/zh). 아직 감지 전(첫 발화)이면 None.
            - None: 언어 자동감지를 방해하지 않도록 한국어 메뉴 어휘 프롬프트를 주지 않는다.
              (프롬프트가 한국어로 편향돼 있으면 "hello" 같은 짧은 영어 발화도 한국어로 오인식되는
              문제가 있었음 — Whisper의 prompt는 스타일/어휘뿐 아니라 언어 자체에도 강하게 영향을 준다)
            - "ko": 메뉴명 오인식 방지용 어휘 힌트(prompt)를 그대로 사용.
            - 그 외: 한국어 어휘 힌트가 오히려 방해되므로 프롬프트 없이 전사하고, Whisper에
              language 를 명시적으로 고정해 재guess(재추측)로 인한 한국어 이탈을 막는다.

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

    lang = language if language in _SUPPORTED_LANGS else None
    # prompt_override: 전화번호처럼 메뉴 어휘 힌트가 방해되는 입력은 호출한 쪽이 힌트를 직접 정한다
    prompt = prompt_override if prompt_override is not None else (_STT_PROMPT if lang == "ko" else None)

    kwargs: dict[str, Any] = dict(
        model=model,
        file=buf,
        response_format="verbose_json" if use_verbose else "json",
    )
    if prompt:
        kwargs["prompt"] = prompt
    if lang:
        # 이미 언어가 고정된 세션이면 Whisper에 직접 지정 — 매 발화마다 다시 추측하다
        # 엉뚱한(주로 한국어로) 언어로 튀는 것을 방지하고 정확도도 올라간다.
        kwargs["language"] = lang

    resp = await client.audio.transcriptions.create(**kwargs)
    text = (getattr(resp, "text", None) or "").strip()

    # 말이 없을 확률이 높은 구간(무음·잡음의 환각)을 먼저 버린다. 문구 목록은 그 뒤에 한 번 더 거른다.
    no_speech = None
    filtered = False   # 이 전사에서 무언가를 환각·에코로 보고 버렸는가(품질 로그용)
    if use_verbose:
        kept_text, no_speech = _drop_no_speech(getattr(resp, "segments", None), NO_SPEECH_DROP)
        if kept_text is not None:
            logger.info("STT no_speech_prob %.2f ≥ %.2f → 환각 구간 제거 (원문 %d자 → %d자)", no_speech, NO_SPEECH_DROP, len(text), len(kept_text))
            text = kept_text
            filtered = True

    # 무음/잡음에 prompt를 그대로 받아쓴 환각이면 빈 텍스트로 처리 → 프론트에서 무시됨
    if _is_prompt_echo(text):
        logger.info("STT prompt echo 감지 → 무시: %s", text[:40])
        text = ""
        filtered = True
    elif _is_hallucination(text):
        logger.info("STT 환각 감지 → 무시: %s", text[:40])
        text = ""
        filtered = True
    else:
        normalized = _normalize_payment_text(text)
        if normalized != text:
            logger.info("STT 결제 키워드 정규화: %s → %s", text[:40], normalized[:40])
            text = normalized

    if use_verbose:
        language = getattr(resp, "language", None)
    else:
        language = _detect_language(text)

    return {
        "text": text,
        "language": language,
        "duration": getattr(resp, "duration", None) if use_verbose else None,
        "no_speech_prob": no_speech,   # 실제 매장 값 수집·임계값 조정용(whisper-1에서만)
        "filtered": filtered,
    }
