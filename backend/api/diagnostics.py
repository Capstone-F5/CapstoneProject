import json
import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

_log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(_log_dir, exist_ok=True)
_logger = logging.getLogger("gesture_perf")
_logger.setLevel(logging.INFO)
_logger.propagate = False
if not _logger.handlers:
    _handler = RotatingFileHandler(
        os.path.join(_log_dir, "gesture_perf.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _logger.addHandler(_handler)


class GesturePerfIn(BaseModel):
    targetFps: float
    camera: dict | None = None
    sentFps: float
    resultFps: float
    avgInferenceMs: float
    maxInferenceMs: float
    inflight: bool


@router.post("/gesture-performance", status_code=204)
async def gesture_performance(body: GesturePerfIn, request: Request):
    client = request.client.host if request.client else "unknown"
    camera = body.camera or {}
    _logger.info(
        "client=%s camera=%sx%s@%s target_fps=%s sent_fps=%.1f result_fps=%.1f "
        "avg_inference_ms=%.1f max_inference_ms=%.1f inflight=%s",
        client,
        camera.get("width", "?"),
        camera.get("height", "?"),
        camera.get("frameRate", "?"),
        body.targetFps,
        body.sentFps,
        body.resultFps,
        body.avgInferenceMs,
        body.maxInferenceMs,
        body.inflight,
    )


# ── 음성 응답 지연 진단 ─────────────────────────────────────────────────────
# 프론트(ChatPanel)가 발화 한 턴의 단계별 소요 시간(ms)을 보내면 한 줄 JSON으로 남긴다.
# 짧은 발화("네", "어")가 왜 느린지 어느 구간이 병목인지 확인하기 위한 용도.
_voice_logger = logging.getLogger("voice_timing")
_voice_logger.setLevel(logging.INFO)
_voice_logger.propagate = False
if not _voice_logger.handlers:
    _voice_handler = RotatingFileHandler(
        os.path.join(_log_dir, "voice_timing.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    _voice_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _voice_logger.addHandler(_voice_handler)


@router.post("/voice-timing", status_code=204)
async def voice_timing(body: dict, request: Request):
    client = request.client.host if request.client else "unknown"
    # 발화 텍스트는 개인정보가 될 수 있어 길이만 받는다(프론트도 텍스트를 보내지 않음).
    body = {k: v for k, v in body.items() if k != "text"}
    _voice_logger.info("client=%s %s", client, json.dumps(body, ensure_ascii=False, sort_keys=True))
