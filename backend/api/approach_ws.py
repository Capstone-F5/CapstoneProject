"""
흰 지팡이 / 휠체어 접근 감지 WebSocket 엔드포인트.

클라이언트 → 서버:
  binary : JPEG 카메라 프레임 (canvas.toBlob 결과)
  text   : {"type": "user_input"}  — 사용자 터치/입력 신호

서버 → 클라이언트:
  text   : 상태 JSON  {"white_cane_detected", "white_cane_confidence",
                       "wheelchair_detected", "wheelchair_confidence",
                       "active_trigger", "mode_action", "mode_on",
                       "announcement_count", "mode_ended", "confirmed"}
  (안내 음성은 프론트가 사전 녹음 mp3로 재생한다)
"""
from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.approach_service import (
    ApproachSession,
    handle_user_input,
    process_frame_result,
)

router = APIRouter()

# 감지 로그 — 신뢰도 임계값(0.5)과 박스 높이 기준(MIN_BOX_H)을 실제 설치 환경 데이터로 조정하기 위한 값. 영상은 저장하지 않는다.
# 2fps라 매 프레임을 쓰면 너무 많으므로 신뢰도 0.25 이상이거나 mode_on이 바뀔 때만 남긴다.
# 분석: 오탐(사람이 없는데 확정)과 미탐(대상이 있는데 conf가 낮거나 box_h가 작음)을 본다.
_LOG_MIN_CONF = 0.25
_log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(_log_dir, exist_ok=True)
_detect_log = logging.getLogger("approach_detect")
_detect_log.setLevel(logging.INFO)
_detect_log.propagate = False
if not _detect_log.handlers:
    _h = RotatingFileHandler(os.path.join(_log_dir, "approach.log"), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _detect_log.addHandler(_h)


def _log_detection(detection: dict, result: dict, prev_mode: bool) -> None:
    if max(detection["white_cane_confidence"], detection["wheelchair_confidence"]) < _LOG_MIN_CONF and result["mode_on"] == prev_mode:
        return
    c = result["confirmed"]
    _detect_log.info(
        "cane conf=%.2f h=%.2f hit=%s ok=%s | wheel conf=%.2f h=%.2f hit=%s ok=%s | mode_on=%s trigger=%s",
        detection["white_cane_confidence"], detection["white_cane_box_h"], detection["white_cane_detected"], c["white_cane"],
        detection["wheelchair_confidence"], detection["wheelchair_box_h"], detection["wheelchair_detected"], c["wheelchair"],
        result["mode_on"], result["active_trigger"],
    )


@router.websocket("/ws/approach")
async def approach_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    session = ApproachSession()
    prev_mode = False

    try:
        from ai_modules.cv.approach_detector import get_detector
        detector = get_detector()
    except Exception as e:
        await websocket.send_json({"error": f"모델 로드 실패: {e}"})
        await websocket.close(code=1011)
        return

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            # 제어 신호 (user_input 등)
            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                except (json.JSONDecodeError, TypeError):
                    continue

                if payload.get("type") == "user_input":
                    await websocket.send_json(handle_user_input(session))

            # JPEG 카메라 프레임
            elif "bytes" in message:
                jpeg_bytes: bytes = message["bytes"]
                if not jpeg_bytes:
                    continue

                try:
                    detection = await detector.detect(jpeg_bytes)
                except Exception as e:
                    await websocket.send_json({"error": f"추론 실패: {str(e)}"})
                    continue

                result = process_frame_result(
                    session,
                    detection["white_cane_detected"],
                    detection["white_cane_confidence"],
                    detection["wheelchair_detected"],
                    detection["wheelchair_confidence"],
                )
                _log_detection(detection, result, prev_mode)
                prev_mode = result["mode_on"]
                await websocket.send_json(result)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
