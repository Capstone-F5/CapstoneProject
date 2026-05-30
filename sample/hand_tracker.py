import cv2
import mediapipe as mp
import numpy as np


class HandTracker:
    """MediaPipe Hands 래퍼. 프레임에서 손 랜드마크를 추출한다."""

    # MediaPipe 21개 랜드마크 인덱스 상수
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8;  INDEX_PIP = 6;  INDEX_MCP = 5
    MIDDLE_TIP = 12; MIDDLE_PIP = 10
    RING_TIP = 16;   RING_PIP = 14
    PINKY_TIP = 20;  PINKY_PIP = 18

    def __init__(self, config):
        mp_hands = mp.solutions.hands
        self._hands = mp_hands.Hands(
            max_num_hands=config.MAX_HANDS,
            min_detection_confidence=config.DETECTION_CONFIDENCE,
            min_tracking_confidence=config.TRACKING_CONFIDENCE,
        )
        self._draw = mp.solutions.drawing_utils
        self._draw_styles = mp.solutions.drawing_styles
        self._mp_hands = mp_hands

    def process(self, bgr_frame):
        """BGR 프레임을 받아 MediaPipe 결과를 반환한다."""
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True
        return results

    def get_landmarks(self, results, frame_shape):
        """첫 번째 손의 픽셀 좌표 랜드마크 리스트(21개)를 반환한다. 없으면 None."""
        if not results.multi_hand_landmarks:
            return None
        h, w = frame_shape[:2]
        lms = results.multi_hand_landmarks[0].landmark
        return [(int(lm.x * w), int(lm.y * h)) for lm in lms]

    def draw(self, frame, results):
        """카메라 프레임 위에 손 랜드마크와 연결선을 그린다."""
        if not results.multi_hand_landmarks:
            return
        for hand_lms in results.multi_hand_landmarks:
            self._draw.draw_landmarks(
                frame, hand_lms, self._mp_hands.HAND_CONNECTIONS,
                self._draw_styles.get_default_hand_landmarks_style(),
                self._draw_styles.get_default_hand_connections_style(),
            )
