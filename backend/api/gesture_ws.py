import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.gesture_service import detect_gesture_from_landmarks

router = APIRouter()


@router.websocket("/ws/gesture")
async def gesture_ws(websocket: WebSocket):
    """
    클라이언트(브라우저 MediaPipe)로부터 손 랜드마크를 JSON으로 받아 제스처 분석.

    수신 포맷:
        { "hands": [ { "label": "Left"|"Right", "lm": [x0,y0,z0, ... x20,y20,z20] }, ... ] }
    """
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue

            hands_data = payload.get("hands") or []
            result = detect_gesture_from_landmarks(hands_data)

            # tuple → list (JSON 직렬화)
            for hand in result["hands"].values():
                if hand and hand.get("index_position"):
                    hand["index_position"] = list(hand["index_position"])

            await websocket.send_json(result)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
