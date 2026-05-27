class Config:
    # --- 카메라 ---
    CAMERA_ID = 0
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480

    # --- MediaPipe 손 추적 ---
    MAX_HANDS = 1
    DETECTION_CONFIDENCE = 0.7
    TRACKING_CONFIDENCE = 0.5

    # --- 스와이프 감지 ---
    SWIPE_H_THRESHOLD = 0.11
    SWIPE_V_THRESHOLD = 0.09
    SWIPE_AXIS_DOMINANCE = 1.4
    SWIPE_HISTORY_LEN = 30
    SWIPE_WINDOW = 14
    SWIPE_COOLDOWN = 30
    SWIPE_MIN_FRAMES = 8

    # --- OK 제스처 (~3초 유지) ---
    OK_DISTANCE_THRESHOLD = 0.07
    OK_CONFIRM_FRAMES = 85

    # --- 드웰(Dwell) 선택 ---
    DWELL_FRAMES = 35
    DWELL_RADIUS = 45

    # --- 포인팅 커서 ---
    CURSOR_ALPHA = 0.60

    # --- 키오스크 UI ---
    KIOSK_WIDTH = 420
    KIOSK_HEIGHT = 480

    # --- 윈도우 ---
    WINDOW_NAME = "Gesture Kiosk — Barrier-Free Demo"
