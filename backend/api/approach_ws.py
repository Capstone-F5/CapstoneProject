"""
흰 지팡이 접근 감지 WebSocket 엔드포인트.

클라이언트 → 서버:
  binary : JPEG 카메라 프레임 (canvas.toBlob 결과)
  text   : {"type": "user_input"}  — 사용자 터치/입력 신호

서버 → 클라이언트:
  text   : 상태 JSON  {"white_cane_detected", "confidence", "voice_mode_on",
                       "announcement_count", "play_tts", "mode_ended"}
  binary : play_tts=true 일 때 JSON 직후 캐시된 MP3 오디오 바이너리 전송
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.approach_service import (
    ApproachSession,
    get_tts_audio,
    handle_user_input,
    process_frame_result,
)

router = APIRouter()


@router.websocket("/ws/approach")
async def approach_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    session = ApproachSession()

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
                    detected, conf = await detector.detect(jpeg_bytes)
                except Exception as e:
                    await websocket.send_json({"error": f"추론 실패: {str(e)}"})
                    continue

                result = process_frame_result(session, detected, conf)
                await websocket.send_json(result)

                # play_tts=True이면 캐시된 TTS 오디오를 binary 프레임으로 전송
                if result["play_tts"]:
                    try:
                        audio = await get_tts_audio()
                        await websocket.send_bytes(audio)
                    except Exception as e:
                        await websocket.send_json({"error": f"TTS 전송 실패: {str(e)}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
