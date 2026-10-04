"""
STT 엔드포인트.

POST /ai_modules/stt
- multipart/form-data 로 오디오 파일 업로드.
- Whisper-1 + Zero-shot 자동 언어 감지.
- 응답 지연 2초 이내를 위해 AsyncOpenAI 로 비동기 호출.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.stt_service import transcribe_bytes


router = APIRouter(prefix="/ai_modules", tags=["stt"])

# STT 품질 로그 — 환각 필터(no_speech_prob 임계값)를 실제 매장 소음에서 조정하기 위한 값. 발화 텍스트는 남기지 않고 길이만 남긴다.
# 분석: filtered=True인 줄의 no_speech_prob가 정상 발화(filtered=False)와 겹치는지 본다(겹치면 임계값을 올려야 한다).
_log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(_log_dir, exist_ok=True)
_quality = logging.getLogger("stt_quality")
_quality.setLevel(logging.INFO)
_quality.propagate = False
if not _quality.handlers:
    _h = RotatingFileHandler(os.path.join(_log_dir, "stt_quality.log"), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _quality.addHandler(_h)


def _log_quality(kind: str, result: dict) -> None:
    p = result.get("no_speech_prob")
    _quality.info("kind=%s no_speech_prob=%s filtered=%s text_len=%d lang=%s duration=%s", kind,
                  "-" if p is None else f"{p:.3f}", result.get("filtered"), len(result.get("text") or ""),
                  result.get("language"), result.get("duration"))


@router.post("/stt")
async def stt(audio: UploadFile = File(...), language: str | None = Form(None)):
    if not audio.filename:
        raise HTTPException(400, "오디오 파일이 필요합니다.")

    data = await audio.read()
    if not data:
        raise HTTPException(400, "오디오 파일이 비어 있습니다.")

    try:
        result = await transcribe_bytes(data, filename=audio.filename or "audio.webm", language=language)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:  # noqa: BLE001  — OpenAI 호출 오류 사용자 노출
        raise HTTPException(502, f"STT 변환 실패: {e}")

    _log_quality("chat", result)
    return result


# 전화번호 입력용: 메뉴 어휘 힌트 대신 숫자 읽기를 유도하는 프롬프트.
# 예시 번호를 넣지 않는다 — 무음·잡음 녹음에서 Whisper가 프롬프트를 그대로 받아쓰면 가짜 번호가 입력창에 채워진다.
_PHONE_PROMPT = "손님이 휴대전화 번호를 숫자로 또박또박 말합니다."


@router.post("/stt/phone")
async def stt_phone(audio: UploadFile = File(...), language: str | None = Form(None)):
    """한 번 말한 전화번호를 숫자만 뽑아 돌려준다(LLM 없음). 포인트 적립 팝업의 마이크 버튼이 쓴다.

    응답: {"text": 전사 원문, "digits": 숫자만(최대 11자리, 못 알아들었으면 ""), "complete": 11자리인가}
    숫자 판별은 음성 주문의 전화번호 검증과 같은 규칙(action_tools._spoken_digits: "공일공"·"이요" 어미 처리)을 쓴다.
    """
    if not audio.filename:
        raise HTTPException(400, "오디오 파일이 필요합니다.")
    data = await audio.read()
    if not data:
        raise HTTPException(400, "오디오 파일이 비어 있습니다.")

    try:
        result = await transcribe_bytes(data, filename=audio.filename or "audio.webm", language=language or "ko",
                                        prompt_override=_PHONE_PROMPT)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"STT 변환 실패: {e}")

    from ai_modules.llm.action_tools import _spoken_digits   # 지연 임포트: LLM 도구 모듈은 무겁다
    _log_quality("phone", result)
    text = result.get("text", "")
    digits = _spoken_digits(text)[:11]
    return {"text": text, "digits": digits, "complete": len(digits) == 11}
