import os
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'ai_modules', 'cv', 'data_static'
)

GESTURES = ['none', 'ok', 'finger_1', 'finger_2', 'finger_3', 'finger_4', 'finger_5']


class CollectRequest(BaseModel):
    gesture: str
    lm: List[float]  # 63 floats (21 joints × xyz)


def _normalize(flat_lm: list) -> np.ndarray:
    """collect_static.py / gesture_classifier.py 와 동일한 정규화"""
    coords = np.array(flat_lm, dtype=np.float32).reshape(21, 3)
    coords -= coords[0].copy()
    scale = np.linalg.norm(coords[9])
    if scale > 1e-6:
        coords /= scale
    return coords.flatten()


def _count(gesture: str) -> int:
    d = os.path.join(DATA_DIR, gesture)
    if not os.path.exists(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith('.npy')])


@router.post("/api/collect/static")
async def save_static(req: CollectRequest):
    if req.gesture not in GESTURES:
        raise HTTPException(400, f"알 수 없는 제스처: {req.gesture}")
    if len(req.lm) != 63:
        raise HTTPException(400, f"lm 길이 오류: {len(req.lm)} (63 필요)")

    features = _normalize(req.lm)
    save_dir = os.path.join(DATA_DIR, req.gesture)
    os.makedirs(save_dir, exist_ok=True)
    idx  = _count(req.gesture)
    path = os.path.join(save_dir, f"{idx:04d}.npy")
    np.save(path, features)
    return {"saved": idx + 1, "gesture": req.gesture}


@router.get("/api/collect/status")
async def get_status():
    return {g: _count(g) for g in GESTURES}


@router.delete("/api/collect/static/undo/{gesture}")
async def undo_last(gesture: str):
    if gesture not in GESTURES:
        raise HTTPException(400, f"알 수 없는 제스처: {gesture}")
    d = os.path.join(DATA_DIR, gesture)
    if not os.path.exists(d):
        raise HTTPException(404, "데이터 없음")
    files = sorted([f for f in os.listdir(d) if f.endswith('.npy')])
    if not files:
        raise HTTPException(404, "삭제할 샘플 없음")
    os.remove(os.path.join(d, files[-1]))
    return {"deleted": files[-1], "gesture": gesture, "remaining": len(files) - 1}
