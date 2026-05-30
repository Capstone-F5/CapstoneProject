import math
from collections import deque
from enum import Enum
from typing import Optional

import numpy as np


class GestureType(Enum):
    NONE = "none"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    POINT = "point"   # 검지만 펼침 — 커서 이동
    DWELL = "dwell"   # 커서 일정 시간 고정 — 항목 자동 선택
    OK = "ok"         # OK 제스처 — 결제 확인


class GestureDetector:
    def __init__(self, config):
        self._cfg = config
        # 정규화된 (nx, ny) 위치 히스토리 — 스와이프용
        self._history: deque = deque(maxlen=config.SWIPE_HISTORY_LEN)
        self._swipe_cooldown = 0
        self._ok_frames = 0
        self._smooth_cursor = None  # type: Optional[list]

        # 드웰 추적
        self._dwell_anchor = None   # 드웰 시작 커서 위치 (kiosk 좌표)
        self._dwell_frames = 0

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def detect(self, landmarks, frame_shape):
        """
        (GestureType, data) 튜플 반환.

        data 구조:
          POINT  → {"cursor": (kx,ky), "progress": float 0~1}
          DWELL  → {"cursor": (kx,ky)}
          기타   → None
        """
        if landmarks is None:
            self._reset_all()
            return GestureType.NONE, None

        if self._swipe_cooldown > 0:
            self._swipe_cooldown -= 1

        # 팜 센터(손바닥 중심)를 스와이프 기준점으로 사용 — 손목보다 안정적
        palm = self._palm_center(landmarks)
        h, w = frame_shape[:2]
        self._history.append((palm[0] / w, palm[1] / h))  # 정규화 좌표 저장

        # ── 1. OK 제스처 (결제 확인, 최우선) ─────────────────────────────
        if self._is_ok(landmarks, frame_shape):
            self._ok_frames += 1
            self._reset_dwell()
            progress = min(1.0, self._ok_frames / self._cfg.OK_CONFIRM_FRAMES)
            if self._ok_frames >= self._cfg.OK_CONFIRM_FRAMES:
                self._ok_frames = 0
                self._history.clear()
                return GestureType.OK, None
            # 판정 전까지 진행률만 반환 (UI 피드백용)
            return GestureType.NONE, {"ok_progress": progress}
        self._ok_frames = 0

        # ── 2. 포인팅 + 드웰 (검지 펼침) ─────────────────────────────────
        if self._is_pointing(landmarks):
            cursor = self._map_cursor(landmarks, frame_shape)
            progress = self._update_dwell(cursor)

            if progress >= 1.0:
                self._reset_dwell()
                self._history.clear()
                return GestureType.DWELL, {"cursor": cursor}

            return GestureType.POINT, {"cursor": cursor, "progress": progress}

        # 포인팅이 아니면 드웰 초기화
        self._reset_dwell()

        # ── 3. 스와이프 (열린 손바닥 상태에서만 인정) ────────────────────
        if self._swipe_cooldown == 0 and self._is_open_palm(landmarks):
            swipe = self._detect_swipe()
            if swipe != GestureType.NONE:
                self._swipe_cooldown = self._cfg.SWIPE_COOLDOWN
                self._history.clear()
                return swipe, None

        return GestureType.NONE, None

    # ------------------------------------------------------------------ #
    # 손 상태 분류
    # ------------------------------------------------------------------ #

    def _palm_center(self, lms):
        """손바닥 중심: 손목 + 4개 손가락 MCP 관절의 평균."""
        idxs = [0, 5, 9, 13, 17]
        xs = sum(lms[i][0] for i in idxs) / len(idxs)
        ys = sum(lms[i][1] for i in idxs) / len(idxs)
        return (int(xs), int(ys))

    def _finger_states(self, lms):
        """[index_up, middle_up, ring_up, pinky_up] 불리언 리스트."""
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        return [lms[t][1] < lms[p][1] for t, p in zip(tips, pips)]

    def _norm_dist(self, lms, i, j, frame_shape):
        h, w = frame_shape[:2]
        p1 = np.array([lms[i][0] / w, lms[i][1] / h])
        p2 = np.array([lms[j][0] / w, lms[j][1] / h])
        return float(np.linalg.norm(p1 - p2))

    def _is_ok(self, lms, frame_shape):
        """엄지-검지 팁이 가깝고, 나머지 손가락 2개 이상 펼쳐진 경우."""
        if self._norm_dist(lms, 4, 8, frame_shape) >= self._cfg.OK_DISTANCE_THRESHOLD:
            return False
        return sum(self._finger_states(lms)[1:]) >= 2

    def _is_pointing(self, lms):
        """검지만 펼치고 나머지(중지·약지·소지)는 접힌 경우."""
        s = self._finger_states(lms)
        return s[0] and not s[1] and not s[2] and not s[3]

    def _is_open_palm(self, lms):
        """손가락 3개 이상 펼쳐진 경우 — 스와이프용 열린 손 확인."""
        return sum(self._finger_states(lms)) >= 3

    # ------------------------------------------------------------------ #
    # 스와이프 감지 (정규화 좌표 + 축 우세 판정)
    # ------------------------------------------------------------------ #

    def _detect_swipe(self):
        if len(self._history) < self._cfg.SWIPE_MIN_FRAMES:
            return GestureType.NONE

        arr = np.array(self._history)
        # 슬라이딩 윈도우: 전체 히스토리가 아닌 최근 N프레임만 사용
        # → 손이 화면에 오래 머물다가 스와이프해도 정확하게 인식
        window = min(len(arr), self._cfg.SWIPE_WINDOW)
        recent = arr[-window:]

        ndx = float(recent[-1][0] - recent[0][0])
        ndy = float(recent[-1][1] - recent[0][1])
        abs_dx, abs_dy = abs(ndx), abs(ndy)

        dominance = self._cfg.SWIPE_AXIS_DOMINANCE

        if abs_dx >= abs_dy * dominance:
            if abs_dx < self._cfg.SWIPE_H_THRESHOLD:
                return GestureType.NONE
            return GestureType.SWIPE_RIGHT if ndx > 0 else GestureType.SWIPE_LEFT

        elif abs_dy >= abs_dx * dominance:
            if abs_dy < self._cfg.SWIPE_V_THRESHOLD:
                return GestureType.NONE
            return GestureType.SWIPE_DOWN if ndy > 0 else GestureType.SWIPE_UP

        return GestureType.NONE  # 대각선 움직임 → 무시

    # ------------------------------------------------------------------ #
    # 드웰 추적
    # ------------------------------------------------------------------ #

    def _update_dwell(self, cursor):
        """커서 위치가 앵커 반경 안에 머물면 카운트를 올리고 진행률(0~1)을 반환한다."""
        if self._dwell_anchor is None:
            self._dwell_anchor = cursor
            self._dwell_frames = 1
            return 0.0

        dist = math.hypot(cursor[0] - self._dwell_anchor[0],
                          cursor[1] - self._dwell_anchor[1])

        if dist > self._cfg.DWELL_RADIUS:
            # 너무 많이 움직였으면 앵커 갱신
            self._dwell_anchor = cursor
            self._dwell_frames = 1
            return 0.0

        self._dwell_frames += 1
        return min(1.0, self._dwell_frames / self._cfg.DWELL_FRAMES)

    def _reset_dwell(self):
        self._dwell_anchor = None
        self._dwell_frames = 0

    # ------------------------------------------------------------------ #
    # 커서 좌표 매핑 + 스무딩
    # ------------------------------------------------------------------ #

    def _map_cursor(self, lms, frame_shape):
        h, w = frame_shape[:2]
        kw, kh = self._cfg.KIOSK_WIDTH, self._cfg.KIOSK_HEIGHT
        tip = lms[8]  # INDEX_TIP

        raw = [int(tip[0] / w * kw), int(tip[1] / h * kh)]
        raw[0] = max(0, min(kw - 1, raw[0]))
        raw[1] = max(0, min(kh - 1, raw[1]))

        if self._smooth_cursor is None:
            self._smooth_cursor = raw[:]
        else:
            a = self._cfg.CURSOR_ALPHA
            self._smooth_cursor[0] = int(a * self._smooth_cursor[0] + (1 - a) * raw[0])
            self._smooth_cursor[1] = int(a * self._smooth_cursor[1] + (1 - a) * raw[1])

        return tuple(self._smooth_cursor)

    def _reset_all(self):
        self._history.clear()
        self._ok_frames = 0
        self._swipe_cooldown = max(0, self._swipe_cooldown - 1)
        self._smooth_cursor = None
        self._reset_dwell()
