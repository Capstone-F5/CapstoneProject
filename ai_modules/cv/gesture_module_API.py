import cv2
import math
import mediapipe as mp
import numpy as np
import time
from collections import deque, Counter

# 백엔드(패키지 임포트)와 직접 실행(스크립트) 양쪽 지원
try:
    from .gesture_classifier import predict_static, predict_dynamic
except ImportError:
    from gesture_classifier import predict_static, predict_dynamic

# ── MediaPipe ────────────────────────────────────────────────────────────────
hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)

# ── EMA 스무딩 (전체 균등) ──────────────────────────────────────────────────
# 0.55: 안정성과 반응성의 균형. tip만 빨리 해봤지만 포인터/스와이프 모두 흔들려서 통일.
EMA_ALPHA    = 0.55
_smoothed_lm = {"Left": None, "Right": None}

# ── 포인터 전용 One Euro Filter ──────────────────────────────────────────────
# Casiez et al. 2012 — 정지 떨림 제거 + 빠른 동작 즉각 반응을 모두 만족
# min_cutoff↓ = 정지 시 더 부드럽게,  beta↑ = 빠른 움직임에 더 민감
POINTER_MIN_CUTOFF = 0.15   # Hz — 정지 시 cutoff (매우 낮게 → 거의 정지)
POINTER_BETA       = 50.0   # 속도 비례 cutoff 증가량 (높을수록 빠른 동작에 민감)
POINTER_D_CUTOFF   = 1.0    # Hz — 속도 추정 자체에 대한 LPF

# 출력 데드존 — One Euro 후에도 남는 미세 떨림을 한 번 더 잘라냄
# 한 프레임에 이 임계값 미만으로 변하면 이전 출력 유지 → 가만히 있을 때 완전 정지
POINTER_OUTPUT_DEADZONE = 0.0018   # 정규화 좌표 (480 프레임 기준 약 0.9px)
_pointer_output = {"Left": None, "Right": None}


class _OneEuro:
    """One Euro Filter — 단일 채널(x 또는 y)용."""
    __slots__ = ('min_cutoff', 'beta', 'd_cutoff', 'x_prev', 'dx_prev', 't_prev')

    def __init__(self, min_cutoff, beta, d_cutoff):
        self.min_cutoff = min_cutoff
        self.beta       = beta
        self.d_cutoff   = d_cutoff
        self.x_prev  = None
        self.dx_prev = 0.0
        self.t_prev  = None

    def reset(self):
        self.x_prev  = None
        self.dx_prev = 0.0
        self.t_prev  = None

    def __call__(self, x, t):
        if self.x_prev is None:
            self.x_prev = float(x)
            self.t_prev = t
            return self.x_prev
        dt = max(t - self.t_prev, 1e-6)
        dx = (x - self.x_prev) / dt
        a_d = _lpf_alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = _lpf_alpha(cutoff, dt)
        x_hat = a * x + (1 - a) * self.x_prev
        self.x_prev  = x_hat
        self.dx_prev = dx_hat
        self.t_prev  = t
        return x_hat


def _lpf_alpha(cutoff, dt):
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


def _new_pointer_filter():
    return (
        _OneEuro(POINTER_MIN_CUTOFF, POINTER_BETA, POINTER_D_CUTOFF),
        _OneEuro(POINTER_MIN_CUTOFF, POINTER_BETA, POINTER_D_CUTOFF),
    )


_pointer_filters = {"Left": _new_pointer_filter(), "Right": _new_pointer_filter()}

# ── FSM + Debouncing ─────────────────────────────────────────────────────────
CONFIRM_FRAMES    = 3    # 일반 정적 제스처 확정 프레임
CONFIRM_FRAMES_OK = 7    # ok — 연속 7프레임(~0.23초) 유지해야 발화
STATIC_COOLDOWN    = 0.8  # 일반 제스처 재인식 대기
STATIC_COOLDOWN_OK = 0.6  # ok 재인식 대기
_gesture_state  = {
    "Left":  {"candidate": None, "count": 0, "last_fire": 0.0},
    "Right": {"candidate": None, "count": 0, "last_fire": 0.0},
}

# ── 제스처 우선순위 ───────────────────────────────────────────────────────────
# 두 손에서 서로 다른 제스처가 나올 때 높은 쪽을 dominant로 선택
_GESTURE_PRIORITY = {
    'ok':          3,
    'swipe_left':  2, 'swipe_right': 2,
    'swipe_up':    2, 'swipe_down':  2,
    'finger_1':    1, 'finger_2':    1, 'finger_3':    1,
    'finger_4':    1, 'finger_5':    1,
}

# ── finger_* 신뢰도 임계값 (ok 보다 높게 — 오인식 억제) ────────────────────
FINGER_CONF_THRESHOLD = 0.85   # finger_1~5
OK_CONF_THRESHOLD     = 0.9   # ok

# ── 스와이프 ─────────────────────────────────────────────────────────────────
SWIPE_MIN_NORM  = 0.12      # ML 기반 사용 시에도 최소 이동 거리 필터
SWIPE_COOLDOWN  = 0.6
SWIPE_SEQ_LEN   = 20       # ML 분류기 입력 길이 (train_dynamic.py 의 SEQ_LEN 과 일치)
SWIPE_MIN_FRAMES = 15      # 최소 프레임 수 (이 이상 쌓이면 ML 시도)
_wrist_buffers  = {"Left": deque(maxlen=SWIPE_SEQ_LEN), "Right": deque(maxlen=SWIPE_SEQ_LEN)}
_last_swipe     = {"Left": 0.0, "Right": 0.0}

# ── 손가락 개수 스무딩 ───────────────────────────────────────────────────────
_finger_history = {"Left": deque(maxlen=5), "Right": deque(maxlen=5)}

# ── 임계값 ────────────────────────────────────────────────────────────────────
# 손가락 개수: strict (정확한 카운트)
EXTENSION_MARGIN_STRICT = 1.15
# 스와이프 open_hand 체크: lenient (관대하게 — 스와이프 도중 미세한 변화 허용)
EXTENSION_MARGIN_LOOSE  = 1.05
# 스와이프 시 필요한 펴진 손가락 최소 개수 (5개 중)
SWIPE_OPEN_MIN_FINGERS  = 3

class _LM:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)


def _apply_ema(mp_label, raw_landmarks):
    arr  = np.array([[lm.x, lm.y, lm.z] for lm in raw_landmarks])
    prev = _smoothed_lm[mp_label]
    if prev is None:
        _smoothed_lm[mp_label] = arr.copy()
    else:
        _smoothed_lm[mp_label] = EMA_ALPHA * arr + (1 - EMA_ALPHA) * prev
    return [_LM(x, y, z) for x, y, z in _smoothed_lm[mp_label]]


def _smooth_pointer(mp_label, x, y):
    """One Euro Filter + 출력 데드존 — 가만히 있을 때 완전히 정지."""
    fx, fy = _pointer_filters[mp_label]
    t = time.time()
    nx, ny = fx(x, t), fy(y, t)

    last = _pointer_output[mp_label]
    if last is None:
        _pointer_output[mp_label] = (nx, ny)
        return nx, ny

    lx, ly = last
    # 가로/세로 둘 다 데드존 안이면 이전 출력 유지 (시각적 완전 정지)
    if abs(nx - lx) < POINTER_OUTPUT_DEADZONE and abs(ny - ly) < POINTER_OUTPUT_DEADZONE:
        return lx, ly

    _pointer_output[mp_label] = (nx, ny)
    return nx, ny



def _confirm_static(mp_label, gesture):
    state = _gesture_state[mp_label]
    now   = time.time()

    cooldown = STATIC_COOLDOWN_OK if gesture == 'ok' else STATIC_COOLDOWN
    if now - state["last_fire"] < cooldown:
        return None

    if gesture is not None and gesture == state["candidate"]:
        state["count"] += 1
    else:
        state["candidate"] = gesture
        state["count"]     = 1 if gesture else 0

    needed = CONFIRM_FRAMES_OK if gesture == 'ok' else CONFIRM_FRAMES
    if state["count"] >= needed and gesture is not None:
        state["count"]     = 0
        state["last_fire"] = now
        return gesture

    return None


# ── 공개 API ─────────────────────────────────────────────────────────────────

# 클라이언트가 보낸 좌표를 화면 픽셀로 변환할 때 쓰는 가상 캔버스 크기
# (App.jsx의 camToScreen 이 480×360 기준이라 맞춰둠)
VIRTUAL_W = 480
VIRTUAL_H = 360


def _empty_result():
    return {"hands": {"left": None, "right": None}, "total_fingers": 0, "gesture": None}


def _reset_state():
    _wrist_buffers["Left"].clear()
    _wrist_buffers["Right"].clear()
    _smoothed_lm["Left"]     = None
    _smoothed_lm["Right"]    = None
    _pointer_output["Left"]  = None
    _pointer_output["Right"] = None
    for fx, fy in _pointer_filters.values():
        fx.reset()
        fy.reset()


def _process_one_hand(mp_label, raw_landmarks, w, h):
    """공통 처리 — MediaPipe 결과든 클라이언트 전송 데이터든 같은 파이프라인."""
    label     = "right" if mp_label == "Left" else "left"
    landmarks = _apply_ema(mp_label, raw_landmarks)

    # Palm center (MCP 4개 평균)
    _cx = (landmarks[5].x + landmarks[9].x + landmarks[13].x + landmarks[17].x) / 4
    _cy = (landmarks[5].y + landmarks[9].y + landmarks[13].y + landmarks[17].y) / 4
    _wrist_buffers[mp_label].append((_cx, _cy))

    px, py    = _smooth_pointer(mp_label, _cx, _cy)
    index_pos = (int(px * w), int(py * h))

    swipe = _detect_swipe(_wrist_buffers[mp_label], mp_label, landmarks)
    if swipe:
        _confirm_static(mp_label, None)
        gesture = swipe
    else:
        raw = _classify_static(landmarks)
        gesture = _confirm_static(mp_label, raw)

    finger_count = _count_fingers(landmarks, mp_label)

    return label, {
        "gesture":        gesture,
        "finger_count":   finger_count,
        "index_position": index_pos,
    }


def _finalize(hand_data):
    fired = [d["gesture"] for d in hand_data.values() if d.get("gesture")]
    dominant = max(fired, key=lambda g: _GESTURE_PRIORITY.get(g, 0)) if fired else None
    total_fingers = sum(d["finger_count"] for d in hand_data.values())
    return {
        "hands":         {"left": hand_data.get("left"), "right": hand_data.get("right")},
        "total_fingers": total_fingers,
        "gesture":       dominant,
    }


def detect_gesture(frame):
    """서버 사이드 MediaPipe 처리 (테스트 스크립트용 — 백엔드에서는 더 이상 사용 안 함)."""
    try:
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        if not result.multi_hand_landmarks:
            _reset_state()
            return _empty_result()

        h, w, _ = frame.shape
        hand_data = {}
        for lm, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
            mp_label = handedness.classification[0].label
            label, info = _process_one_hand(mp_label, lm.landmark, w, h)
            hand_data[label] = info
        return _finalize(hand_data)

    except Exception as e:
        return {"hands": {"left": None, "right": None}, "total_fingers": 0, "gesture": None, "error": str(e)}


def detect_gesture_from_landmarks(hands_payload):
    """
    클라이언트(브라우저 MediaPipe)에서 추출한 손 랜드마크를 받아 처리.

    hands_payload: [{"label": "Left"|"Right", "lm": [x0,y0,z0, x1,y1,z1, ... x20,y20,z20]}, ...]
    """
    try:
        if not hands_payload:
            _reset_state()
            return _empty_result()

        hand_data = {}
        for hand in hands_payload:
            mp_label = hand.get("label", "Right")
            flat = hand.get("lm") or []
            if len(flat) < 63:
                continue
            # 63 floats → 21개 LM 객체
            raw = [_LM(flat[i*3], flat[i*3+1], flat[i*3+2]) for i in range(21)]
            label, info = _process_one_hand(mp_label, raw, VIRTUAL_W, VIRTUAL_H)
            hand_data[label] = info
        return _finalize(hand_data)

    except Exception as e:
        return {"hands": {"left": None, "right": None}, "total_fingers": 0, "gesture": None, "error": str(e)}


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _dist3d(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5


def _hand_size(landmarks):
    return _dist3d(landmarks[0], landmarks[9])


def _is_finger_extended(landmarks, tip_idx, pip_idx, margin=EXTENSION_MARGIN_STRICT):
    wrist = landmarks[0]
    return _dist3d(landmarks[tip_idx], wrist) > _dist3d(landmarks[pip_idx], wrist) * margin


def _is_thumb_extended(landmarks, margin=1.05):
    return _dist3d(landmarks[4], landmarks[5]) > _dist3d(landmarks[3], landmarks[5]) * margin


def _count_fingers(landmarks, mp_label):
    """정확한 손가락 개수 — strict 마진 + 다수결"""
    count = int(_is_thumb_extended(landmarks))
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        if _is_finger_extended(landmarks, tip, pip, EXTENSION_MARGIN_STRICT):
            count += 1
    _finger_history[mp_label].append(count)
    return Counter(_finger_history[mp_label]).most_common(1)[0][0]


def _classify_static(landmarks):
    label, conf = predict_static(landmarks, confidence_threshold=0.0)
    if label is not None:
        min_conf = FINGER_CONF_THRESHOLD if label.startswith('finger_') else OK_CONF_THRESHOLD
        if conf >= min_conf:
            return label
    return None


def _is_open_hand_for_swipe(landmarks):
    """
    스와이프용 관대한 펴짐 체크.
    - lenient 마진(1.05)
    - 5개 중 N개 이상 펴지면 통과 (모든 손가락 완벽히 펴지지 않아도 됨)
    """
    extended = int(_is_thumb_extended(landmarks, margin=1.0))
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        if _is_finger_extended(landmarks, tip, pip, EXTENSION_MARGIN_LOOSE):
            extended += 1
    return extended >= SWIPE_OPEN_MIN_FINGERS


def _detect_swipe(buffer, mp_label, landmarks):
    if len(buffer) < SWIPE_MIN_FRAMES:
        return None
    now = time.time()
    if now - _last_swipe[mp_label] < SWIPE_COOLDOWN:
        return None
    if not _is_open_hand_for_swipe(landmarks):
        return None

    dx   = buffer[-1][0] - buffer[0][0]
    dy   = buffer[-1][1] - buffer[0][1]
    if (dx ** 2 + dy ** 2) ** 0.5 < SWIPE_MIN_NORM:
        return None

    direction, _ = predict_dynamic(list(buffer))
    if direction is not None:
        _last_swipe[mp_label] = now
        buffer.clear()
    return direction
