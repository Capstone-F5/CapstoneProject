"""수화 숫자(0~9) 검출 — YOLO 추론 래퍼.

모델(finger_count_best.pt)은 손 하나를 박스 하나로 잡고, 클래스가 그 손이 나타내는
숫자('0'~'9')다. 집계 규칙은 손이 하나면 그 숫자, 둘이면 합산.

i3-8100 CPU 기준 imgsz=640에서 프레임당 약 49ms(20fps)로, 목표인 3~4fps에 여유가 크다.
그래서 학습 해상도인 640을 그대로 쓴다 — 낮춰서 얻을 게 없다.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import cv2
import numpy as np

MODEL_PATH = Path(__file__).parent / "models" / "finger_count_best.pt"
IMGSZ = 640
# 두 손을 동시에 보려면 두 번째 손이 부분적으로 가려지거나 각도가 달라도 잡아야 한다.
# 0.5 → 0.40으로 낮춰 두 손 검출률을 높이고, 오검출은 MAX_HANDS=2 상한으로 제한한다.
CONF_THRESHOLD = 0.40
MAX_HANDS = 2


class FingerCounter:
    def __init__(self, model_path: str | Path = MODEL_PATH) -> None:
        from ultralytics import YOLO

        self._model = YOLO(str(model_path))
        self._names = self._model.names
        # 추론 하나가 CPU 4스레드를 다 쓴다. 동시에 돌리면 서로 느려지기만 하므로 직렬화한다.
        self._lock = asyncio.Lock()

    async def detect(self, jpeg_bytes: bytes) -> dict:
        async with self._lock:
            return await asyncio.to_thread(self._detect_sync, jpeg_bytes)

    def _detect_sync(self, jpeg_bytes: bytes) -> dict:
        img = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("JPEG 디코딩 실패")

        result = self._model.predict(
            img, imgsz=IMGSZ, conf=CONF_THRESHOLD, device="cpu", verbose=False
        )[0]

        hands = [
            {"digit": int(self._names[int(box.cls)]), "conf": round(float(box.conf), 3)}
            for box in result.boxes
        ]
        # 손은 최대 두 개다. 오검출이 섞여도 신뢰도 높은 것부터 두 개만 쓴다.
        hands.sort(key=lambda h: h["conf"], reverse=True)
        hands = hands[:MAX_HANDS]

        return {"hands": hands, "total": sum(h["digit"] for h in hands)}


_detector: FingerCounter | None = None


def get_detector() -> FingerCounter:
    global _detector
    if _detector is None:
        _detector = FingerCounter()
    return _detector
