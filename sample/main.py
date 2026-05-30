"""
Gesture Kiosk — Barrier-Free Demo
===================================
실행:  python main.py
종료:  'q' 키

WebSocket: ws://localhost:8765 으로 제스처 이벤트를 전송합니다.
React 프론트엔드를 별도 브라우저에서 실행하세요.
"""

import sys
import time
import json
import asyncio
import threading
import cv2
import numpy as np
import websockets

from config import Config
from hand_tracker import HandTracker
from gesture_detector import GestureDetector, GestureType


# ── WebSocket 서버 ──────────────────────────────────────────────────────────

_ws_clients: set = set()
_ws_store: dict = {}   # {'loop': ..., 'queue': ...}


async def _ws_handler(websocket):
    _ws_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        _ws_clients.discard(websocket)


async def _broadcast_loop(queue: asyncio.Queue):
    while True:
        msg = await queue.get()
        if _ws_clients:
            await asyncio.gather(
                *[c.send(msg) for c in list(_ws_clients)],
                return_exceptions=True,
            )


async def _ws_main():
    queue: asyncio.Queue = asyncio.Queue()
    _ws_store["queue"] = queue
    _ws_store["loop"] = asyncio.get_running_loop()

    async with websockets.serve(_ws_handler, "0.0.0.0", 8765):
        print("[WS] 제스처 서버 시작 → ws://0.0.0.0:8765 (네트워크 전체 허용)")
        await _broadcast_loop(queue)


def _start_ws_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_ws_main())


def broadcast(cfg: Config, gesture: GestureType, data):
    """제스처 이벤트를 모든 WebSocket 클라이언트에게 전송한다."""
    if "loop" not in _ws_store or "queue" not in _ws_store:
        return

    cursor_norm = None
    progress = 0.0
    ok_progress = 0.0

    if data and isinstance(data, dict):
        cursor = data.get("cursor")
        if cursor:
            # 정규화 좌표 (0~1) — React 측에서 화면 크기에 맞게 변환
            cursor_norm = [
                cursor[0] / cfg.KIOSK_WIDTH,
                cursor[1] / cfg.KIOSK_HEIGHT,
            ]
        progress = data.get("progress", 0.0)
        ok_progress = data.get("ok_progress", 0.0)

    msg = json.dumps({
        "gesture": gesture.value,
        "cursor": cursor_norm,
        "progress": progress,
        "ok_progress": ok_progress,
    })
    _ws_store["loop"].call_soon_threadsafe(_ws_store["queue"].put_nowait, msg)


# ── 카메라 HUD ──────────────────────────────────────────────────────────────

GESTURE_LABEL = {
    GestureType.SWIPE_UP:    "↑ 위 스와이프",
    GestureType.SWIPE_DOWN:  "↓ 아래 스와이프",
    GestureType.SWIPE_LEFT:  "← 왼쪽 스와이프",
    GestureType.SWIPE_RIGHT: "→ 오른쪽 스와이프",
    GestureType.POINT:       "☞ 포인팅",
    GestureType.DWELL:       "✅ 선택!",
    GestureType.OK:          "👌 OK",
    GestureType.NONE:        "",
}

GESTURE_COLOR = {
    GestureType.SWIPE_UP:    (0, 200, 100),
    GestureType.SWIPE_DOWN:  (0, 200, 100),
    GestureType.SWIPE_LEFT:  (0, 160, 220),
    GestureType.SWIPE_RIGHT: (0, 160, 220),
    GestureType.POINT:       (200, 140, 0),
    GestureType.DWELL:       (0,  220, 100),
    GestureType.OK:          (0,  180, 60),
    GestureType.NONE:        (200, 200, 200),
}


def overlay_hud(frame: np.ndarray, gesture: GestureType, fps: float,
                ok_progress: float = 0.0):
    h, w = frame.shape[:2]
    label = GESTURE_LABEL.get(gesture, "")
    color = GESTURE_COLOR.get(gesture, (200, 200, 200))

    if label:
        cv2.rectangle(frame, (8, h - 44), (min(len(label) * 14 + 20, w - 8), h - 8),
                      (0, 0, 0), -1)
        cv2.putText(frame, label, (14, h - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

    cv2.putText(frame, f"FPS {fps:.0f}", (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 255, 180), 1, cv2.LINE_AA)

    if ok_progress > 0.0:
        bar_w = 200
        bx = w // 2 - bar_w // 2
        by = h - 18
        cv2.rectangle(frame, (bx, by), (bx + bar_w, by + 10), (40, 40, 40), -1)
        filled = int(bar_w * ok_progress)
        cv2.rectangle(frame, (bx, by), (bx + filled, by + 10), (0, 220, 80), -1)
        cv2.putText(frame, "OK holding...", (bx, by - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 80), 1, cv2.LINE_AA)

    # WS 연결 상태 표시
    client_count = len(_ws_clients)
    ws_color = (0, 220, 80) if client_count > 0 else (0, 100, 200)
    ws_text = f"WS {client_count} connected" if client_count > 0 else "WS waiting..."
    cv2.putText(frame, ws_text, (8, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, ws_color, 1, cv2.LINE_AA)


def overlay_guide(frame: np.ndarray):
    guides = [
        "↑↓ Swipe : scroll/category",
        "← Swipe  : back",
        "→ Swipe  : next/select",
        "Point    : cursor",
        "Dwell 1s : select",
        "OK       : confirm",
    ]
    x, y0 = frame.shape[1] - 200, 10
    for i, g in enumerate(guides):
        cv2.putText(frame, g, (x, y0 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 220, 255), 1, cv2.LINE_AA)


# ── 메인 루프 ───────────────────────────────────────────────────────────────

def run():
    cfg = Config()

    # WebSocket 서버를 백그라운드 스레드에서 시작
    ws_thread = threading.Thread(target=_start_ws_thread, daemon=True)
    ws_thread.start()

    cap = cv2.VideoCapture(cfg.CAMERA_ID)
    if not cap.isOpened():
        print("[ERROR] 카메라를 열 수 없습니다. CAMERA_ID를 확인하세요.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)

    tracker  = HandTracker(cfg)
    detector = GestureDetector(cfg)

    cv2.namedWindow(cfg.WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(cfg.WINDOW_NAME, cfg.FRAME_WIDTH, cfg.FRAME_HEIGHT)

    prev_time = time.time()
    last_gesture = GestureType.NONE

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] 프레임 읽기 실패")
            continue

        frame = cv2.flip(frame, 1)

        results  = tracker.process(frame)
        landmarks = tracker.get_landmarks(results, frame.shape)
        gesture, data = detector.detect(landmarks, frame.shape)

        # 모든 프레임마다 WebSocket으로 상태 전송 (NONE 포함)
        broadcast(cfg, gesture, data)

        ok_progress = 0.0
        if data and isinstance(data, dict):
            ok_progress = data.get("ok_progress", 0.0)

        if gesture != GestureType.NONE:
            last_gesture = gesture
        elif last_gesture != GestureType.NONE:
            last_gesture = GestureType.NONE

        tracker.draw(frame, results)

        now = time.time()
        fps = 1.0 / max(now - prev_time, 1e-5)
        prev_time = now

        display_gesture = gesture if gesture != GestureType.NONE else last_gesture
        overlay_hud(frame, display_gesture, fps, ok_progress)
        overlay_guide(frame)

        cv2.imshow(cfg.WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
