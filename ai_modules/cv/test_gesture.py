"""
PC 로컬 제스처 테스트

- 학습된 ML 모델의 실시간 추론 결과 표시 (신뢰도 포함)
- 손가락 개수, 제스처, 검지 포인터 시각화
- 'q' 종료
"""

import cv2
import mediapipe as mp
from gesture_module_API import detect_gesture
from gesture_classifier import predict_static


# ── 카메라 ───────────────────────────────────────────────────────────────────

def open_camera():
    backends = [
        (cv2.CAP_MSMF,  "Media Foundation"),
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_ANY,   "Default"),
    ]
    for idx in (0, 1):
        for backend, name in backends:
            cap = cv2.VideoCapture(idx, backend)
            if not cap.isOpened():
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None and frame.std() > 5.0:
                    print(f"Camera: index={idx}, backend={name}")
                    return cap
            cap.release()
    return None


# ── MediaPipe (raw 예측용 — debouncing 우회) ────────────────────────────────

_hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)
_draw = mp.solutions.drawing_utils


def raw_predict(frame):
    """디바운싱 없이 원시 ML 추론 결과 반환 (각 손마다)"""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = _hands.process(rgb)
    out = []
    if not result.multi_hand_landmarks:
        return out
    for lm in result.multi_hand_landmarks:
        label, conf = predict_static(lm.landmark, confidence_threshold=0.0)
        out.append({
            'label':     label or 'none',
            'confidence': conf,
            'landmarks': lm,
        })
    return out


# ── 화면 텍스트 헬퍼 ────────────────────────────────────────────────────────

def put(frame, text, pos, color=(255, 255, 255), scale=0.7, thick=2):
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thick + 2)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick)


def main():
    print("\nCamera connecting...")
    cap = open_camera()
    if cap is None:
        print("Camera open failed.")
        return

    print("\nGesture test running. Press 'q' to quit.\n")

    frame_count = 0
    PRINT_EVERY = 15

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # 1) 풀 파이프라인 (debouncing 포함)
            full = detect_gesture(frame)
            # 2) 원시 ML 추론 (즉시 반응)
            raw  = raw_predict(frame)

            # 랜드마크 그리기
            for r in raw:
                _draw.draw_landmarks(frame, r['landmarks'],
                                     mp.solutions.hands.HAND_CONNECTIONS)

            # ── 상단 패널: 풀 파이프라인 결과 (실제 사용 동작) ──────────────
            cv2.rectangle(frame, (0, 0), (w, 130), (30, 30, 30), -1)
            put(frame, "== Pipeline output (with debouncing) ==",
                (10, 25), color=(100, 220, 255), scale=0.6)

            left  = full["hands"]["left"]
            right = full["hands"]["right"]

            left_txt  = f"L: {left['finger_count']}f, {left['gesture'] or '-'}"   if left  else "L: -"
            right_txt = f"R: {right['finger_count']}f, {right['gesture'] or '-'}" if right else "R: -"
            put(frame, left_txt,  (10, 55), color=(0, 220, 255), scale=0.7)
            put(frame, right_txt, (10, 85), color=(255, 180, 0), scale=0.7)
            put(frame, f"Total: {full['total_fingers']}f   Gesture: {full.get('gesture') or '-'}",
                (10, 115), color=(255, 255, 100), scale=0.65)

            # ── 하단 패널: 원시 ML 예측 (디바운싱 없음, 신뢰도 표시) ────────
            cv2.rectangle(frame, (0, h - 90), (w, h), (30, 30, 30), -1)
            put(frame, "== Raw ML prediction (confidence) ==",
                (10, h - 65), color=(180, 255, 180), scale=0.55)
            if raw:
                for i, r in enumerate(raw):
                    color = (100, 255, 100) if r['confidence'] > 0.7 else (200, 200, 200)
                    put(frame, f"hand{i+1}: {r['label']:10s} {r['confidence']:.2f}",
                        (10 + i * 280, h - 30), color=color, scale=0.7)
            else:
                put(frame, "no hand detected", (10, h - 30),
                    color=(100, 100, 100), scale=0.6)

            # 검지 포인터
            if left and left.get("index_position"):
                ix, iy = left["index_position"]
                cv2.circle(frame, (ix, iy), 10, (0, 220, 255), -1)
            if right and right.get("index_position"):
                ix, iy = right["index_position"]
                cv2.circle(frame, (ix, iy), 10, (255, 180, 0), -1)

            cv2.imshow("Gesture Test", frame)

            # 콘솔 출력
            frame_count += 1
            if frame_count % PRINT_EVERY == 0 and raw:
                parts = [f"{r['label']}({r['confidence']:.2f})" for r in raw]
                print(f"[{frame_count:05d}] raw={', '.join(parts)} | "
                      f"pipeline={full.get('gesture') or '-'}")

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
