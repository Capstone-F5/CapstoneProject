"""
학습된 정적 제스처 분류기 추론 래퍼.

- 모델 파일이 없으면 None 반환 (gesture_module_API가 규칙 기반으로 fallback)
- 모델 파일이 있으면 자동 로드
"""

import os
import numpy as np

_MODEL_PATH         = os.path.join(os.path.dirname(__file__), 'models', 'static_mlp.pkl')
_DYNAMIC_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'dynamic_mlp.pkl')

_model_data = None
_load_attempted = False

_dynamic_model_data    = None
_dynamic_load_attempted = False


def _try_load():
    """모델을 한 번만 로드 시도. 실패 시 None 유지."""
    global _model_data, _load_attempted
    if _load_attempted:
        return _model_data
    _load_attempted = True

    if not os.path.exists(_MODEL_PATH):
        print(f"[classifier] 모델 파일 없음 — 규칙 기반으로 동작: {_MODEL_PATH}")
        return None

    try:
        import joblib
        _model_data = joblib.load(_MODEL_PATH)
        print(f"[classifier] 정적 제스처 모델 로드됨. 클래스: {_model_data['classes']}")
    except Exception as e:
        print(f"[classifier] 모델 로드 실패: {e}")
        _model_data = None

    return _model_data


def _try_load_dynamic():
    global _dynamic_model_data, _dynamic_load_attempted
    if _dynamic_load_attempted:
        return _dynamic_model_data
    _dynamic_load_attempted = True

    if not os.path.exists(_DYNAMIC_MODEL_PATH):
        print(f"[classifier] Dynamic model not found — rule-based swipe active: {_DYNAMIC_MODEL_PATH}")
        return None

    try:
        import joblib as _jl
        _dynamic_model_data = _jl.load(_DYNAMIC_MODEL_PATH)
        print(f"[classifier] Dynamic model loaded. Classes: {_dynamic_model_data['classes']}")
    except Exception as e:
        print(f"[classifier] Dynamic model load failed: {e}")

    return _dynamic_model_data


def normalize_landmarks(landmarks):
    """수집 스크립트와 동일한 정규화 (손목 원점, 손 크기 스케일)"""
    coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
    coords -= coords[0].copy()
    scale = np.linalg.norm(coords[9])
    if scale > 1e-6:
        coords /= scale
    return coords.flatten().reshape(1, -1)


def predict_static(landmarks, confidence_threshold=0.7):
    """
    정적 제스처 분류.

    Returns:
        (label, confidence) 또는 (None, 0.0)
        - 모델 없음 / 신뢰도 낮음 / 예외 시 (None, 0.0)
    """
    data = _try_load()
    if data is None:
        return None, 0.0

    try:
        features = normalize_landmarks(landmarks)
        proba    = data['model'].predict_proba(features)[0]
        idx      = int(np.argmax(proba))
        label    = data['classes'][idx]
        conf     = float(proba[idx])

        if conf < confidence_threshold:
            return None, conf
        if label == 'none':
            return None, conf
        return label, conf
    except Exception as e:
        print(f"[classifier] 추론 오류: {e}")
        return None, 0.0


def predict_dynamic(wrist_xy_seq, confidence_threshold=0.65):
    """
    Dynamic (swipe) gesture classification from wrist trajectory.

    Args:
        wrist_xy_seq: array-like (N, 2)  wrist x,y in MediaPipe coords (0~1).
                      N should be >= 8; will be resampled to model's SEQ_LEN.
        confidence_threshold: minimum confidence to accept prediction.

    Returns:
        (direction, confidence)  e.g. ('swipe_left', 0.91)
        or (None, 0.0) when uncertain or 'none' class wins.
    """
    data = _try_load_dynamic()
    if data is None:
        return None, 0.0

    try:
        seq = np.array(wrist_xy_seq, dtype=np.float32)
        if seq.ndim != 2 or seq.shape[1] != 2 or len(seq) < 4:
            return None, 0.0

        target = int(data.get('seq_len', 20))

        # Resample to training SEQ_LEN
        n = len(seq)
        if n != target:
            old_t = np.linspace(0, 1, n)
            new_t = np.linspace(0, 1, target)
            seq   = np.stack(
                [np.interp(new_t, old_t, seq[:, d]) for d in range(2)],
                axis=-1
            ).astype(np.float32)

        # Extract same features as training (must stay in sync with train_dynamic.py)
        rel      = seq - seq[0]
        vel      = np.diff(rel, axis=0)

        net        = rel[-1]
        abs_net    = np.abs(net)
        abs_sum    = float(abs_net.sum()) + 1e-6
        x_dom      = float(abs_net[0] / abs_sum)
        net_x_norm = float(net[0] / abs_sum)
        net_y_norm = float(net[1] / abs_sum)
        speeds     = np.linalg.norm(vel, axis=1)
        max_speed  = float(speeds.max())
        path_len   = float(speeds.sum()) + 1e-6
        straight   = float(np.linalg.norm(net) / path_len)
        mid_disp   = float(np.linalg.norm(rel[target // 2]))

        summary  = np.array([
            net[0], net[1],
            x_dom, net_x_norm, net_y_norm,
            max_speed, straight, mid_disp,
        ], dtype=np.float32)

        features = np.concatenate([rel.flatten(), vel.flatten(), summary]).reshape(1, -1)

        proba = data['model'].predict_proba(features)[0]
        idx   = int(np.argmax(proba))
        label = data['classes'][idx]
        conf  = float(proba[idx])

        if conf < confidence_threshold or label == 'none':
            return None, conf
        return label, conf

    except Exception as e:
        print(f"[classifier] Dynamic prediction error: {e}")
        return None, 0.0
