"""
LSTM 제스처 인식 모델 학습용 데이터 수집 스크립트

사용법:
    python collect_data.py

조작법:
    SPACE  - 녹화 시작
    S      - 현재 샘플 저장
    R      - 현재 샘플 다시 녹화
    N      - 다음 제스처로 이동
    Q      - 종료

수집 결과:
    ai_modules/cv/data/<제스처명>/<숫자>.npy
    각 파일 shape: (SEQUENCE_LENGTH, 63)  ← 30프레임 × 21관절 × 3(x,y,z)
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import time

# ── 설정 ────────────────────────────────────────────────────────────────────

GESTURES = [
    'swipe_left',
    'swipe_right',
    'swipe_up',
    'swipe_down',
    'ok',
    'finger_1',
    'finger_2',
    'finger_3',
    'finger_4',
    'finger_5',
]

SEQUENCE_LENGTH  = 30    # 한 샘플당 프레임 수
SAMPLES_TARGET   = 60    # 제스처당 목표 샘플 수
DATA_DIR         = os.path.join(os.path.dirname(__file__), 'data')
COUNTDOWN_SEC    = 2     # 녹화 전 카운트다운(초)

# ── MediaPipe ────────────────────────────────────────────────────────────────

hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.75,
    min_tracking_confidence=0.65,
)


# ── 랜드마크 정규화 ─────────────────────────────────────────────────────────

def normalize_landmarks(landmarks):
    """
    손목(0번)을 원점으로, 손 크기(손목~중지MCP 거리)로 스케일 정규화.
    카메라 위치·거리에 무관한 상대 좌표를 반환.
    shape: (63,)  ← 21관절 × 3(x,y,z)
    """
    coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])  # (21, 3)

    # 손목 기준 평행 이동
    origin = coords[0].copy()
    coords -= origin

    # 손 크기로 정규화 (손목~중지 MCP 거리)
    scale = np.linalg.norm(coords[9])
    if scale > 1e-6:
        coords /= scale

    return coords.flatten()  # (63,)


# ── 보조 함수 ────────────────────────────────────────────────────────────────

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def count_saved(gesture):
    d = os.path.join(DATA_DIR, gesture)
    if not os.path.exists(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith('.npy')])


def next_index(gesture):
    return count_saved(gesture)


def put_text(frame, text, pos, color=(255, 255, 255), scale=0.7, thickness=2):
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    gesture_idx = 0

    # 상태: 'ready' | 'countdown' | 'recording' | 'preview'
    state          = 'ready'
    sequence       = []       # 현재 녹화 중인 프레임 시퀀스
    countdown_start = None

    print("\n=== 데이터 수집 시작 ===")
    print("조작: SPACE=녹화시작  S=저장  R=다시녹화  N=다음제스처  Q=종료\n")

    while gesture_idx < len(GESTURES):
        gesture = GESTURES[gesture_idx]
        saved   = count_saved(gesture)

        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)  # 미러
        h, w, _ = frame.shape

        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        # 랜드마크 그리기
        if result.multi_hand_landmarks:
            for lm in result.multi_hand_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, lm, mp.solutions.hands.HAND_CONNECTIONS
                )

        # ── 상태별 처리 ────────────────────────────────────────────────────
        if state == 'countdown':
            elapsed = time.time() - countdown_start
            remain  = COUNTDOWN_SEC - elapsed
            if remain <= 0:
                state    = 'recording'
                sequence = []
            else:
                put_text(frame, f"준비... {remain:.1f}초", (w//2 - 80, h//2),
                         color=(0, 200, 255), scale=1.2, thickness=2)

        elif state == 'recording':
            if result.multi_hand_landmarks:
                lm_data = normalize_landmarks(result.multi_hand_landmarks[0].landmark)
                sequence.append(lm_data)

            prog = len(sequence)
            cv2.rectangle(frame, (20, h - 40), (20 + int((w - 40) * prog / SEQUENCE_LENGTH), h - 20),
                          (0, 200, 100), -1)
            put_text(frame, f"녹화 중... {prog}/{SEQUENCE_LENGTH}", (20, h - 50), color=(0, 255, 100))

            if len(sequence) >= SEQUENCE_LENGTH:
                state = 'preview'

        elif state == 'preview':
            put_text(frame, "S: 저장   R: 다시녹화", (20, h - 50), color=(255, 220, 0))

        # ── HUD ────────────────────────────────────────────────────────────
        # 상단 정보 패널
        cv2.rectangle(frame, (0, 0), (w, 80), (30, 30, 30), -1)
        put_text(frame, f"제스처: {gesture}", (10, 28), color=(100, 220, 255), scale=0.85)
        put_text(frame, f"저장됨: {saved} / {SAMPLES_TARGET}", (10, 58),
                 color=(100, 255, 100) if saved >= SAMPLES_TARGET else (200, 200, 200),
                 scale=0.7)
        put_text(frame, f"[{gesture_idx+1}/{len(GESTURES)}]  SPACE=시작  N=다음  Q=종료",
                 (w - 350, 28), scale=0.55, color=(180, 180, 180))

        if state == 'ready':
            put_text(frame, "SPACE 눌러서 녹화 시작", (w//2 - 130, h//2),
                     color=(255, 255, 100), scale=0.9)

        cv2.imshow("Gesture Data Collector", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' ') and state == 'ready':
            state           = 'countdown'
            countdown_start = time.time()
            sequence        = []
        elif key == ord('s') and state == 'preview':
            if len(sequence) >= SEQUENCE_LENGTH:
                save_dir = os.path.join(DATA_DIR, gesture)
                ensure_dir(save_dir)
                idx  = next_index(gesture)
                path = os.path.join(save_dir, f"{idx:04d}.npy")
                np.save(path, np.array(sequence[:SEQUENCE_LENGTH]))
                print(f"  저장: {gesture} [{idx+1}/{SAMPLES_TARGET}]")
                state = 'ready'
                if count_saved(gesture) >= SAMPLES_TARGET:
                    print(f"\n✅ '{gesture}' 수집 완료! N 눌러서 다음으로.")
            else:
                print("  시퀀스가 너무 짧습니다. 다시 녹화하세요.")
                state = 'ready'
        elif key == ord('r'):
            state    = 'ready'
            sequence = []
        elif key == ord('n'):
            if saved < SAMPLES_TARGET:
                ans = input(f"\n'{gesture}' 샘플이 {saved}개입니다 ({SAMPLES_TARGET}개 목표). 그래도 넘어가시겠어요? (y/N): ")
                if ans.lower() != 'y':
                    continue
            gesture_idx += 1
            state       = 'ready'
            sequence    = []
            if gesture_idx < len(GESTURES):
                print(f"\n▶ 다음 제스처: {GESTURES[gesture_idx]}")

    cap.release()
    cv2.destroyAllWindows()

    # 수집 결과 요약
    print("\n=== 수집 결과 요약 ===")
    total = 0
    for g in GESTURES:
        n = count_saved(g)
        total += n
        status = "✅" if n >= SAMPLES_TARGET else f"⚠ ({n}/{SAMPLES_TARGET})"
        print(f"  {g:15s}: {n}개  {status}")
    print(f"\n  총 {total}개 샘플 수집 완료")
    print(f"  저장 위치: {DATA_DIR}")
    print("\n다음 단계: python train_lstm.py")


if __name__ == "__main__":
    main()
