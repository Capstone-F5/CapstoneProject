"""흰 지팡이 / 휠체어 접근 감지 - TFLite 추론 래퍼.

- temp/main.py의 전처리/추론/파싱 로직을 서버 비동기 환경에 맞게 이식.
- 인터프리터는 싱글턴으로 유지하고 asyncio.Lock으로 직렬화.
- 모델은 3클래스(person=0, white_cane=1, wheelchair=2)로 재학습됨 (Issue #66).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import cv2
import numpy as np

_tflite = None
try:
    import tflite_runtime.interpreter as _tflite
except ImportError:
    try:
        # Windows/최신 Python에서는 tflite_runtime 휠이 없어 후속 패키지(ai-edge-litert)를 쓴다.
        from ai_edge_litert import interpreter as _tflite  # type: ignore
    except ImportError:
        try:
            import tensorflow as tf  # type: ignore
            _tflite = tf.lite  # type: ignore
        except ImportError:
            _tflite = None

PERSON_CLASS_ID = 0
WHITE_CANE_CLASS_ID = 1
WHEELCHAIR_CLASS_ID = 2
CONFIDENCE_THRESHOLD = 0.5
# 박스 높이가 화면의 이 비율 미만이면 너무 멀다고 보고 무시. 데이터 없이 정한 가정치 — approach.log를 보고 조정한다.
MIN_BOX_H = 0.15
MODEL_PATH = Path(__file__).parent / "models" / "best_int8.tflite"
PT_MODEL_PATH = Path(__file__).parent / "models" / "best.pt"


def _get_approach_thresholds() -> tuple[float, float]:
    """키오스크 개발자 설정에서 실시간 신뢰도/박스높이 임계값을 조회한다."""
    try:
        from core.kiosk_settings import get_kiosk_settings
        cfg = get_kiosk_settings().get("approach", {})
        return (
            float(cfg.get("confidence_threshold", CONFIDENCE_THRESHOLD)),
            float(cfg.get("min_box_h", MIN_BOX_H)),
        )
    except Exception:
        return CONFIDENCE_THRESHOLD, MIN_BOX_H


class ApproachDetector:
    def __init__(self, model_path: str | Path = MODEL_PATH) -> None:
        self._lock = asyncio.Lock()
        self._yolo_model = None
        if _tflite is not None:
            self.interpreter = _tflite.Interpreter(model_path=str(model_path))
            self.interpreter.allocate_tensors()

            self._in = self.interpreter.get_input_details()[0]
            self._out = self.interpreter.get_output_details()[0]

            shape = self._in["shape"]
            self._h, self._w = int(shape[1]), int(shape[2])
            self._dtype = self._in["dtype"]
            self._in_scale, self._in_zero = self._in["quantization"]
        else:
            # Windows Python 3.13 등 TFLite 런타임이 없는 개발 환경에서는 동일 가중치의 best.pt(Ultralytics YOLO)로 폴백
            from ultralytics import YOLO
            self._yolo_model = YOLO(str(PT_MODEL_PATH))

    def _preprocess(self, jpeg_bytes: bytes) -> np.ndarray:
        buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("JPEG 디코딩 실패")
        img = cv2.resize(img, (self._w, self._h))
        img = cv2.cvtColor(img, (cv2.COLOR_BGR2RGB))

        if self._dtype == np.int8:
            f = img.astype(np.float32) / 255.0
            if self._in_scale != 0.0:
                q = (f / self._in_scale + self._in_zero).astype(np.int8)
            else:
                q = (img.astype(np.int32) - 128).astype(np.int8)
            return np.expand_dims(q, axis=0)
        return np.expand_dims(img.astype(np.float32) / 255.0, axis=0)

    def _parse_output(self, raw: np.ndarray) -> dict:
        out_scale, out_zero = self._out["quantization"]
        if self._out["dtype"] == np.int8:
            raw = (raw.astype(np.float32) - out_zero) * out_scale

        out = raw[0]
        if out.shape[0] < out.shape[1]:
            out = np.transpose(out)

        scores = out[:, 4:]
        if scores.size == 0:
            return {
                "white_cane_detected": False, "white_cane_confidence": 0.0, "white_cane_box_h": 0.0,
                "wheelchair_detected": False, "wheelchair_confidence": 0.0, "wheelchair_box_h": 0.0,
            }

        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        def best_for(class_id: int) -> tuple[float, float]:
            """클래스의 최고 신뢰도와 그 박스의 높이(화면 대비 0~1)."""
            mask = class_ids == class_id
            if not np.any(mask):
                return 0.0, 0.0
            i = int(np.flatnonzero(mask)[np.argmax(confidences[mask])])
            return float(confidences[i]), float(out[i, 3])

        white_cane_conf, white_cane_h = best_for(WHITE_CANE_CLASS_ID)
        wheelchair_conf, wheelchair_h = best_for(WHEELCHAIR_CLASS_ID)
        conf_thresh, min_box_h = _get_approach_thresholds()

        # 멀리 있는 대상(박스가 작음)은 감지로 보지 않는다 — 키오스크 앞에 선 사람만 대상.
        return {
            "white_cane_detected": white_cane_conf > conf_thresh and white_cane_h >= min_box_h,
            "white_cane_confidence": white_cane_conf,
            "white_cane_box_h": white_cane_h,
            "wheelchair_detected": wheelchair_conf > conf_thresh and wheelchair_h >= min_box_h,
            "wheelchair_confidence": wheelchair_conf,
            "wheelchair_box_h": wheelchair_h,
        }

    def detect_sync(self, jpeg_bytes: bytes) -> dict:
        if self._yolo_model is not None:
            buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("JPEG 디코딩 실패")
            img_h = float(img.shape[0]) or 1.0
            res = self._yolo_model.predict(img, imgsz=640, conf=0.05, device="cpu", verbose=False)[0]
            white_cane_conf, white_cane_h = 0.0, 0.0
            wheelchair_conf, wheelchair_h = 0.0, 0.0
            for box in res.boxes:
                cls_id = int(box.cls)
                conf = float(box.conf)
                xyxy = box.xyxy[0].tolist()
                box_h = max(0.0, min(1.0, (xyxy[3] - xyxy[1]) / img_h))
                if cls_id == WHITE_CANE_CLASS_ID and conf > white_cane_conf:
                    white_cane_conf, white_cane_h = conf, box_h
                elif cls_id == WHEELCHAIR_CLASS_ID and conf > wheelchair_conf:
                    wheelchair_conf, wheelchair_h = conf, box_h
            conf_thresh, min_box_h = _get_approach_thresholds()
            return {
                "white_cane_detected": white_cane_conf > conf_thresh and white_cane_h >= min_box_h,
                "white_cane_confidence": white_cane_conf,
                "white_cane_box_h": white_cane_h,
                "wheelchair_detected": wheelchair_conf > conf_thresh and wheelchair_h >= min_box_h,
                "wheelchair_confidence": wheelchair_conf,
                "wheelchair_box_h": wheelchair_h,
            }

        data = self._preprocess(jpeg_bytes)
        self.interpreter.set_tensor(self._in["index"], data)
        self.interpreter.invoke()
        raw = self.interpreter.get_tensor(self._out["index"])
        return self._parse_output(raw)

    async def detect(self, jpeg_bytes: bytes) -> dict:
        """반환: {white_cane_detected, white_cane_confidence, wheelchair_detected, wheelchair_confidence}"""
        async with self._lock:
            return await asyncio.to_thread(self.detect_sync, jpeg_bytes)


_detector: ApproachDetector | None = None


def get_detector() -> ApproachDetector:
    global _detector
    if _detector is None:
        _detector = ApproachDetector()
    return _detector
