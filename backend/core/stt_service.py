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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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
NO_SPEECH_DROP = float(os.getenv("STT_NO_SPEECH_DROP", "0.65"))
# 구간 평균 토큰 로그확률(avg_logprob) 하한. 배경 음악·먼 거리 웅얼거림·소음을 억지로 글자로 맞춘 구간은 보통 -1.0 미만으로 떨어진다.
LOGPROB_DROP = float(os.getenv("STT_LOGPROB_DROP", "-1.0"))
# "네", "단품", "매장" 등 1~2음절 핵심 단답은 문맥 정보가 짧아 avg_logprob가 다소 낮을 수 있으므로 완화된 하한을 적용한다.
SHORT_WORD_LOGPROB_DROP = float(os.getenv("STT_SHORT_LOGPROB_DROP", "-1.35"))
# 구간 압축비(compression_ratio) 상한. 배경 음악 박자나 소음에 의해 같은 글자·구절이 반복되는 루프 환각(>2.4)을 차단한다.
COMPRESSION_DROP = float(os.getenv("STT_COMPRESSION_DROP", "2.4"))

# 짧은 핵심 단답(완화된 avg_logprob 기준 적용 대상)
_SHORT_CORE_WORDS: frozenset[str] = frozenset({
    "네", "예", "응", "어", "아니", "아니요", "아뇨", "맞아", "맞아요", "좋아", "좋아요", "그래", "오케이",
    "매장", "포장", "단품", "세트", "카드", "현금", "페이", "결제", "주문", "시작", "취소", "물", "콜라", "사이다",
    "yes", "no", "ok", "okay", "here", "togo", "card", "cash",
    "はい", "いいえ", "店内", "持ち帰り", "カード", "現金",
    "好", "好的", "是的", "不要", "堂食", "打包",
})

# whisper-1 verbose_json이 반환하는 언어명/코드 중 키오스크가 지원하는 언어 집합.
# 무음·배경 음악·잡음이 들어왔을 때 Whisper가 nynorsk, welsh, russian, arabic 등으로 오감지하는 환각을 차단한다.
_WHISPER_ALLOWED_LANGS: frozenset[str] = frozenset({
    "ko", "korean",
    "en", "english",
    "ja", "japanese",
    "zh", "chinese", "mandarin", "cantonese",
})

# 유튜브 마무리 멘트·배경 음악·방송 자막 등 무음·잡음에 Whisper가 지어내는 전형적 문장. 공백을 없애고 소문자로 비교한다(띄어쓰기 변형 대응).
_HALLUCINATION_FRAGMENTS: frozenset[str] = frozenset({
    # 한국어 유튜브/방송 자막 환각
    "시청해주셔서 감사합니다", "시청해 주셔서 감사합니다",
    "구독과 좋아요", "좋아요와 구독", "알림 설정", "알림설정",
    "다음 영상에서", "다음 영상",
    "한글자막", "자막 제공", "자막제공", "영상을 시청", "이 영상은",
    "mbc 뉴스", "kbs 뉴스", "sbs 뉴스", "ytn 뉴스", "jtbc 뉴스",
    "제작 지원", "협찬", "배달의민족",
    # 배경 음악·효과음 캡션 환각
    "[음악]", "(음악)", "[박수]", "(박수)", "[웃음]", "(웃음)", "[노래]", "(노래)",
    "인기가요", "뮤직뱅크", "음악중심", "노래방",
    # 영어 — 언어를 정하지 않은 첫 발화에서 무음·잡음에 실제로 나온다("Thank you for watching.", 2026-10-04 실험)
    "thank you for watching", "thanks for watching", "please subscribe", "like and subscribe",
    "amara.org", "subtitles by", "subtitles provided", "transcribed by", "copyright",
    "[music]", "(music)", "[applause]", "(applause)", "[laughter]", "music playing",
    # 일본어·중국어·러시아어
    "ありがとうございました", "ご視聴ありがとう", "チャンネル登録", "字幕",
    "感谢您的观看", "感谢观看", "请订阅", "点赞订阅", "謝謝觀看", "优优独播剧场", "불법복제",
    "благодарю за просмотр", "субтитры", "редактор субтитров",
})
_HALLUCINATION_COMPACT: frozenset[str] = frozenset(re.sub(r"\s+", "", f.lower()) for f in _HALLUCINATION_FRAGMENTS)
# 문장 전체가 이것뿐이면 환각이다(무음에 "you"가 단독으로 나온다). "thank you"처럼 실제 손님이 말할 수 있는 것은 넣지 않는다.
_HALLUCINATION_EXACT: frozenset[str] = frozenset({
    "you", "bye", "the", "a", "i", "um", "uh", "ah", "oh", "hmm", "mm", "eh",
    "음", "으음", "흠", "아", "오", "우", "으", "하", "후", "헤", "히", "크", "스", "쓰",
})
# 음악 기호나 무의미한 감탄사/한숨 반복 패턴 ("♪ ~ ♪", "음 음 으으", "하하하", "아 아 아")
_MUSIC_SYMBOL_RE = re.compile(r"[♪♬♩♭♮♯]")
_FILLER_REPEAT_RE = re.compile(
    r"^(?:(?:[아어음으하헤호후흠흐우오크스쓰]\s*[.,!?~\-…]*\s*){2,}|[아어음으하헤호후흠흐우오크스쓰]\s*(?:\.{2,}|…)+)$"
)

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
    """Whisper 전형적 환각(유튜브 자막·방송 멘트·배경 음악 기호·무의미한 추임새 반복 등) 감지."""
    if not text:
        return False
    if _MUSIC_SYMBOL_RE.search(text):
        return True
    if _FILLER_REPEAT_RE.match(text.strip()):
        return True
    t = re.sub(r"\s+", "", text.lower())
    if not re.search(r"[0-9a-z가-힣぀-ヿ一-鿿]", t):
        return True   # "."·"…"처럼 글자가 하나도 없으면 말이 아니다
    clean = t.strip(".,!?~-…'\"()[]")
    if clean in _HALLUCINATION_EXACT:
        return True
    return any(frag in t for frag in _HALLUCINATION_COMPACT)


def _is_unsupported_language(detected_lang: str | None) -> bool:
    """whisper-1 verbose_json의 language가 키오스크 지원 언어(한/영/일/중) 외의 언어(nynorsk, welsh, russian 등)이면
    배경 음악·잡음이 엉뚱한 외국어로 오감지된 환각으로 판정한다."""
    if not detected_lang:
        return False
    norm = detected_lang.strip().lower()
    return norm not in _WHISPER_ALLOWED_LANGS


def _seg_attr(seg: Any, key: str) -> Any:
    if isinstance(seg, dict):
        return seg.get(key)
    return getattr(seg, key, None)


def _filter_segments(
    segments,
    no_speech_threshold: float = NO_SPEECH_DROP,
    logprob_threshold: float = LOGPROB_DROP,
    compression_threshold: float = COMPRESSION_DROP,
) -> dict[str, Any]:
    """구간별 no_speech_prob · avg_logprob · compression_ratio 3중 신뢰도 필터.

    - no_speech_prob >= no_speech_threshold: 무음·잡음 구간
    - avg_logprob < logprob_threshold: 배경 음악·원거리 대화를 억지로 전사한 저신뢰 구간
      (단, 1~2음절 핵심 단답은 SHORT_WORD_LOGPROB_DROP 완화 기준 적용)
    - compression_ratio > compression_threshold: 동일 음절·문구 반복 루프 환각

    Returns:
        {
            "kept_text": str | None (버린 구간이 없으면 None — 원문 유지),
            "max_no_speech": float | None,
            "min_logprob": float | None,
            "max_compression": float | None,
            "drop_reasons": list[str],
        }
    """
    no_speech_probs: list[float] = []
    logprobs: list[float] = []
    compressions: list[float] = []
    kept: list[str] = []
    drop_reasons: list[str] = []
    dropped = False

    for seg in segments or []:
        seg_text = (_seg_attr(seg, "text") or "").strip()
        p_ns = _seg_attr(seg, "no_speech_prob")
        p_lp = _seg_attr(seg, "avg_logprob")
        c_rt = _seg_attr(seg, "compression_ratio")

        if p_ns is not None:
            no_speech_probs.append(float(p_ns))
        if p_lp is not None:
            logprobs.append(float(p_lp))
        if c_rt is not None:
            compressions.append(float(c_rt))

        # 1) no_speech_prob 검사
        if p_ns is not None and float(p_ns) >= no_speech_threshold:
            dropped = True
            drop_reasons.append("no_speech")
            continue

        # 2) compression_ratio 검사 (반복 환각 루프)
        if c_rt is not None and float(c_rt) > compression_threshold:
            dropped = True
            drop_reasons.append("high_compression")
            continue

        # 3) avg_logprob 검사 (저신뢰 전사; 짧은 핵심 단답은 완화된 임계값 적용)
        if p_lp is not None:
            compact_seg = re.sub(r"[\s.,!?~]+", "", seg_text.lower())
            eff_lp_thresh = (
                min(logprob_threshold, SHORT_WORD_LOGPROB_DROP)
                if compact_seg in _SHORT_CORE_WORDS
                else logprob_threshold
            )
            if float(p_lp) < eff_lp_thresh:
                dropped = True
                drop_reasons.append("low_logprob")
                continue

        kept.append(seg_text)

    return {
        "kept_text": (" ".join(t for t in kept if t).strip() if dropped else None),
        "max_no_speech": max(no_speech_probs) if no_speech_probs else None,
        "min_logprob": min(logprobs) if logprobs else None,
        "max_compression": max(compressions) if compressions else None,
        "drop_reasons": drop_reasons,
    }


def _drop_no_speech(
    segments,
    threshold: float = NO_SPEECH_DROP,
    logprob_threshold: float = LOGPROB_DROP,
    compression_threshold: float = COMPRESSION_DROP,
) -> tuple[str | None, float | None]:
    """구간별 신뢰도 필터 래퍼 (하위 호환 시그니처 유지).
    (남은 텍스트 또는 None, 전체 구간 중 최대 no_speech_prob)를 돌려준다."""
    res = _filter_segments(
        segments,
        no_speech_threshold=threshold,
        logprob_threshold=logprob_threshold,
        compression_threshold=compression_threshold,
    )
    return res["kept_text"], res["max_no_speech"]


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
        from openai import AsyncOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


_SUPPORTED_LANGS = {"ko", "en", "ja", "zh"}
_fw_model: Any = None


def _get_faster_whisper_model():
    """선택적 로컬 faster-whisper 모델 로더 (STT_BACKEND=faster_whisper 또는 벤치마크 비교용)."""
    global _fw_model
    if _fw_model is None:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        device = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
        compute_type = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8" if device == "cpu" else "float16")
        model_id = os.getenv("FASTER_WHISPER_MODEL", "large-v3-turbo")
        _fw_model = WhisperModel(model_id, device=device, compute_type=compute_type)
    return _fw_model


def _postprocess_transcription(
    raw_text: str,
    *,
    use_verbose: bool,
    segments: Any = None,
    raw_language: str | None = None,
) -> dict[str, Any]:
    """세그먼트 신뢰도 필터·언어 검증·프롬프트 에코·환각 문구 필터·결제 정규화를 순차 적용."""
    text = (raw_text or "").strip()
    no_speech = None
    avg_logprob = None
    compression_ratio = None
    filtered = False
    drop_reason: str | None = None

    if use_verbose and segments is not None:
        try:
            from core.kiosk_settings import get_kiosk_settings
            _mcfg = get_kiosk_settings().get("mic", {})
            seg_res = _filter_segments(
                segments,
                no_speech_threshold=float(_mcfg.get("no_speech_threshold", NO_SPEECH_DROP)),
                logprob_threshold=float(_mcfg.get("logprob_threshold", LOGPROB_DROP)),
                compression_threshold=float(_mcfg.get("compression_threshold", COMPRESSION_DROP)),
            )
        except Exception:
            seg_res = _filter_segments(segments)
        no_speech = seg_res["max_no_speech"]
        avg_logprob = seg_res["min_logprob"]
        compression_ratio = seg_res["max_compression"]
        if seg_res["kept_text"] is not None:
            drop_reason = ",".join(dict.fromkeys(seg_res["drop_reasons"])) or "segment_filter"
            logger.info(
                "STT 세그먼트 신뢰도 필터(%s) → 구간 제거 (no_speech=%s, logprob=%s, comp=%s, 원문 %d자 → %d자)",
                drop_reason, no_speech, avg_logprob, compression_ratio, len(text), len(seg_res["kept_text"]),
            )
            text = seg_res["kept_text"]
            filtered = True

    # whisper-1 자동 언어 감지에서 키오스크 지원 언어(한/영/일/중) 외의 언어가 나오면 잡음/음악 환각으로 차단
    if use_verbose and text and _is_unsupported_language(raw_language):
        logger.info("STT 미지원 언어 환각 감지(lang=%s) → 무시: %s", raw_language, text[:40])
        text = ""
        filtered = True
        drop_reason = drop_reason or f"unsupported_lang:{raw_language}"

    # 무음/잡음에 prompt를 그대로 받아쓴 환각이면 빈 텍스트로 처리 → 프론트에서 무시됨
    if text and _is_prompt_echo(text):
        logger.info("STT prompt echo 감지 → 무시: %s", text[:40])
        text = ""
        filtered = True
        drop_reason = drop_reason or "prompt_echo"
    elif text and _is_hallucination(text):
        logger.info("STT 환각 감지 → 무시: %s", text[:40])
        text = ""
        filtered = True
        drop_reason = drop_reason or "hallucination"
    elif text:
        normalized = _normalize_payment_text(text)
        if normalized != text:
            logger.info("STT 결제 키워드 정규화: %s → %s", text[:40], normalized[:40])
            text = normalized

    language = raw_language if use_verbose else _detect_language(text)
    return {
        "text": text,
        "language": language,
        "no_speech_prob": no_speech,
        "avg_logprob": avg_logprob,
        "compression_ratio": compression_ratio,
        "filtered": filtered,
        "drop_reason": drop_reason,
    }


async def transcribe_bytes(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
    prompt_override: str | None = None,
    *,
    engine_override: str | None = None,
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
        engine_override: 벤치마크용 엔진 강제 지정 ("whisper-1" | "gpt-4o-mini-transcribe" | "faster-whisper").

    Returns:
        { "text": str, "language": str | None, "duration": float | None, "no_speech_prob": float | None,
          "avg_logprob": float | None, "compression_ratio": float | None, "filtered": bool, "drop_reason": str | None }
    """
    backend = engine_override or os.getenv("STT_BACKEND", "openai")
    lang = language if language in _SUPPORTED_LANGS else None
    prompt = prompt_override if prompt_override is not None else (_STT_PROMPT if lang == "ko" else None)

    # 선택적 로컬 faster-whisper 실행 경로
    if backend in ("faster_whisper", "faster-whisper"):
        import asyncio
        fw = _get_faster_whisper_model()

        def _run_fw():
            segments_gen, info = fw.transcribe(
                io.BytesIO(audio_bytes),
                language=lang,
                initial_prompt=prompt,
                no_speech_threshold=NO_SPEECH_DROP,
                logprob_threshold=LOGPROB_DROP,
                compression_ratio_threshold=COMPRESSION_DROP,
                condition_on_previous_text=False,
                temperature=0.0,
                vad_filter=True,
            )
            segs = list(segments_gen)
            raw = " ".join((s.text or "").strip() for s in segs).strip()
            return raw, segs, info

        raw_text, segs, info = await asyncio.to_thread(_run_fw)
        post = _postprocess_transcription(
            raw_text,
            use_verbose=True,
            segments=segs,
            raw_language=getattr(info, "language", None),
        )
        post["duration"] = getattr(info, "duration", None)
        return post

    model = (
        engine_override
        if engine_override in ("whisper-1", "gpt-4o-mini-transcribe", "gpt-4o-transcribe")
        else os.getenv("OPENAI_STT_MODEL", "whisper-1")
    )
    client = _get_client()

    buf = io.BytesIO(audio_bytes)
    buf.name = filename  # SDK가 확장자로 mime 추론

    # whisper-1은 verbose_json으로 언어 감지 및 세그먼트 신뢰도(no_speech_prob, avg_logprob, compression_ratio) 제공.
    # 신규 모델(gpt-4o-*-transcribe)은 json/text만 지원 → 텍스트 문자 기반 언어 추론.
    use_verbose = model == "whisper-1"

    kwargs: dict[str, Any] = dict(
        model=model,
        file=buf,
        response_format="verbose_json" if use_verbose else "json",
        temperature=0.0,  # 잡음·음악 구간에서 temperature 상승 샘플링으로 인한 가사/문장 창작 차단
    )
    if prompt:
        kwargs["prompt"] = prompt
    if lang:
        # 이미 언어가 고정된 세션이면 Whisper에 직접 지정 — 매 발화마다 다시 추측하다
        # 엉뚱한(주로 한국어로) 언어로 튀는 것을 방지하고 정확도도 올라간다.
        kwargs["language"] = lang

    resp = await client.audio.transcriptions.create(**kwargs)
    raw_text = (getattr(resp, "text", None) or "").strip()

    post = _postprocess_transcription(
        raw_text,
        use_verbose=use_verbose,
        segments=getattr(resp, "segments", None) if use_verbose else None,
        raw_language=getattr(resp, "language", None) if use_verbose else None,
    )
    post["duration"] = getattr(resp, "duration", None) if use_verbose else None
    return post
