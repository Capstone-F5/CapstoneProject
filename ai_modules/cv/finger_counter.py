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
# 같은 손이 두 박스로 이중 검출되는 것을 막는 IoU 임계값.
# 두 박스가 이 이상 겹치면 신뢰도 낮은 쪽을 제거한다.
DEDUP_IOU = 0.40


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

        # xyxy 박스 + 메타 추출
        raw = [
            {
                "digit": int(self._names[int(box.cls)]),
                "conf":  round(float(box.conf), 3),
                "xyxy":  box.xyxy[0].tolist(),
            }
            for box in result.boxes
        ]
        raw.sort(key=lambda h: h["conf"], reverse=True)

        # 이중 검출 제거: 신뢰도 높은 박스부터 순서대로 유지하고,
        # 이미 선택된 박스와 IoU가 DEDUP_IOU 이상이면 같은 손으로 보고 버린다.
        kept: list[dict] = []
        for cand in raw:
            if any(_iou(cand["xyxy"], k["xyxy"]) >= DEDUP_IOU for k in kept):
                continue
            kept.append(cand)
            if len(kept) == MAX_HANDS:
                break

        hands = [{"digit": h["digit"], "conf": h["conf"]} for h in kept]
        return {"hands": hands, "total": sum(h["digit"] for h in hands)}


def _iou(a: list[float], b: list[float]) -> float:
    """두 xyxy 박스의 IoU (Intersection over Union)."""
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


_detector: FingerCounter | None = None


def get_detector() -> FingerCounter:
    global _detector
    if _detector is None:
        _detector = FingerCounter()
    return _detector
