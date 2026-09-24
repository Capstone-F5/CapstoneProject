"""수화 숫자(0~9) 인식 WebSocket 엔드포인트.

클라이언트 → 서버:
  binary : JPEG 카메라 프레임

서버 → 클라이언트:
  text   : {"hands": [{"digit": 3, "conf": 0.94}], "total": 3}
           {"error": "..."}

프레임마다 응답을 하나씩 돌려주므로, 클라이언트는 응답을 받은 뒤 다음 프레임을 보내
속도를 맞춘다. 무작정 밀어 넣으면 추론보다 수신이 빨라져 지연만 쌓인다.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/finger")
async def finger_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        from ai_modules.cv.finger_counter import get_detector

        # 첫 연결이 모델 로딩(수 초)을 부담한다. 이벤트 루프를 막지 않도록 스레드로 뺀다.
        detector = await asyncio.to_thread(get_detector)
    except Exception as e:  # noqa: BLE001
        await websocket.send_json({"error": f"모델 로드 실패: {e}"})
        await websocket.close(code=1011)
        return

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break
            if "bytes" not in message:
                continue

            jpeg_bytes: bytes = message["bytes"]
            if not jpeg_bytes:
                continue

            try:
                result = await detector.detect(jpeg_bytes)
            except Exception as e:  # noqa: BLE001
                await websocket.send_json({"error": f"추론 실패: {e}"})
                continue

            await websocket.send_json(result)

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
