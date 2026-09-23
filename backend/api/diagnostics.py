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
