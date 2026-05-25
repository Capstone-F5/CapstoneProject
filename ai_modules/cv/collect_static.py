"""
정적 제스처 데이터 수집 — 단일 프레임 캡처

사용법:
    python collect_static.py

조작법:
    SPACE   - 현재 제스처로 1샘플 저장
    N       - 다음 제스처로 이동
    P       - 이전 제스처로 이동
    Z       - 마지막 샘플 1개 삭제 (실수 복구)
    Q       - 종료

수집 팁:
    - 각 클래스 80개 이상 권장
    - 손을 다양한 위치/각도/거리에서 보여주기
    - 왼손/오른손 골고루 (좌우 반전 데이터까지 포함됨)
    - 'none' 클래스는 일반적인 손 모양 (주먹, 무의미한 모양)을 넣어 오인식 방지

저장 형식:
    ai_modules/cv/data_static/<제스처명>/<index>.npy
    각 .npy shape: (63,)  ← 21관절 × 3(x,y,z), 정규화됨
"""

import cv2
import mediapipe as mp
import numpy as np
import os

# ── 설정 ────────────────────────────────────────────────────────────────────

GESTURES = [
    'none',       # 손 있지만 특정 제스처 아님 (오인식 방지용)
    'ok',
    'finger_1',
    'finger_2',
    'finger_3',
    'finger_4',
    'finger_5',
]

SAMPLES_TARGET = 150
DATA_DIR       = os.path.join(os.path.dirname(__file__), 'data_static')

# 클래스별 수집 팁 — UI에 표시
CLASS_HINTS = {
    'none':     [
        ">> 핀치 직전: 엄지-검지 가깝지만 안 닿음",
        ">> 주먹 / 손가락 반쯤 구부림",
        ">> 손가락 모두 펴거나 벌린 상태",
        ">> 검지만 살짝 구부린 상태",
        ">> 다양한 각도·거리에서 자연스러운 손 모양",
    ],
    'ok':       [
        ">> 엄지-검지 끝 확실히 붙이기 (핀치)",
        ">> 나머지 손가락 펴도 되고 접어도 됨",
        ">> 정면/측면/위아래 다양한 각도",
        ">> 카메라에서 가까울 때 / 멀 때 모두",
        ">> 왼손/오른손 번갈아 가며 수집",
    ],
    'finger_1': [">> 검지만 펴기 (엄지 접음)", ">> 다양한 각도/거리"],
    'finger_2': [">> 검지+중지 펴기 (V자)", ">> 나머지 접기"],
    'finger_3': [">> 검지+중지+약지 펴기"],
    'finger_4': [">> 엄지 제외 4개 펴기"],
    'finger_5': [">> 손 전체 펴기 (5개 모두)"],
}

# ── MediaPipe ────────────────────────────────────────────────────────────────

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)


def normalize_landmarks(landmarks):
    """
    손목(0번)을 원점으로, 손목~중지MCP(9번) 거리로 스케일 정규화.
    카메라 위치·거리·기울기에 무관한 상대 좌표를 반환.
    shape: (63,)
    """
    coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])  # (21, 3)
    origin = coords[0].copy()
    coords -= origin
    scale = np.linalg.norm(coords[9])
    if scale > 1e-6:
        coords /= scale
    return coords.flatten()


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def count_saved(gesture):
    d = os.path.join(DATA_DIR, gesture)
    if not os.path.exists(d):
        return 0
    return len([f for f in os.listdir(d) if f.endswith('.npy')])


def delete_last(gesture):
    d = os.path.join(DATA_DIR, gesture)
    if not os.path.exists(d):
        return False
    files = sorted([f for f in os.listdir(d) if f.endswith('.npy')])
    if not files:
        return False
    os.remove(os.path.join(d, files[-1]))
    return True


def put_text(frame, text, pos, color=(255, 255, 255), scale=0.7, thickness=2):
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


def _frame_is_valid(frame):
    """프레임이 노이즈인지 검사 — 픽셀 표준편차가 너무 낮으면 (단색) 거부"""
    if frame is None or frame.size == 0:
        return False
    # 일반 카메라 영상은 std > 15 이상. 노이즈/단색은 매우 낮거나 매우 고름.
    return float(frame.std()) > 5.0


def open_camera():
    """
    Windows 카메라 백엔드 호환성 처리.
    - MSMF (Media Foundation): 최신 Win10/11에서 보통 가장 안정적
    - DSHOW: 구형 카메라
    - MJPG FOURCC 설정으로 압축 포맷 강제 (노이즈 방지)
    """
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

            # 압축 포맷 강제 — DSHOW에서 raw 포맷 문제로 노이즈 나는 거 방지
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # 첫 프레임이 정상 영상인지 확인 (몇 프레임 워밍업)
            valid = False
            for _ in range(10):
                ret, frame = cap.read()
                if ret and _frame_is_valid(frame):
                    valid = True
                    break

            if valid:
                print(f"카메라 연결 성공: index={idx}, backend={name}")
                return cap
            cap.release()
    return None


def main():
    print("\n카메라 연결 중...")
    cap = open_camera()
    if cap is None:
        print("\n❌ 카메라를 열 수 없습니다. 다음을 확인하세요:")
        print("   1) 프론트엔드 브라우저 탭을 닫았는지 (카메라 점유 해제)")
        print("   2) Windows 설정 → 개인 정보 → 카메라 → '데스크톱 앱이 카메라에 액세스' 허용")
        print("   3) 다른 화상 앱(Zoom, Teams 등) 종료")
        return

    gesture_idx = 0
    last_saved_label = ""
    flash_counter = 0   # 캡처 시 깜빡임 효과

    print("\n=== 정적 제스처 수집 ===")
    print("SPACE=저장  N=다음  P=이전  Z=실수취소  Q=종료\n")

    fail_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            fail_count += 1
            if fail_count > 30:
                print("카메라 프레임 읽기 실패가 지속됩니다. 종료합니다.")
                break
            continue
        fail_count = 0

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        hand_detected = False
        features = None

        if result.multi_hand_landmarks:
            hand_detected = True
            for lm in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)
            features = normalize_landmarks(result.multi_hand_landmarks[0].landmark)

        # 캡처 시 시각 피드백
        if flash_counter > 0:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 255, 0), 10)
            flash_counter -= 1

        gesture = GESTURES[gesture_idx]
        saved   = count_saved(gesture)

        # ── 상단 패널 ──────────────────────────────────────────────────────
        hints = CLASS_HINTS.get(gesture, [])
        panel_h = 90 + max(0, len(hints) - 1) * 22
        cv2.rectangle(frame, (0, 0), (w, panel_h), (30, 30, 30), -1)
        put_text(frame, f"[{gesture_idx+1}/{len(GESTURES)}] Gesture: {gesture}",
                 (10, 32), color=(100, 220, 255), scale=0.9)

        progress_color = (100, 255, 100) if saved >= SAMPLES_TARGET else (255, 200, 100)
        put_text(frame, f"Saved: {saved} / {SAMPLES_TARGET}",
                 (10, 64), color=progress_color, scale=0.7)

        # 진행률 바
        bar_w = int((w - 220) * min(saved / SAMPLES_TARGET, 1.0))
        cv2.rectangle(frame, (210, 50), (210 + bar_w, 72), progress_color, -1)
        cv2.rectangle(frame, (210, 50), (w - 10, 72), (100, 100, 100), 1)

        # 수집 팁
        for ti, hint in enumerate(hints):
            put_text(frame, hint, (10, 90 + ti * 22), color=(200, 200, 120), scale=0.52, thickness=1)

        # ── 하단 패널 ──────────────────────────────────────────────────────
        cv2.rectangle(frame, (0, h - 60), (w, h), (30, 30, 30), -1)
        if hand_detected:
            put_text(frame, "Press SPACE to capture", (10, h - 25),
                     color=(100, 255, 100), scale=0.7)
        else:
            put_text(frame, "Hand not detected", (10, h - 25),
                     color=(100, 100, 255), scale=0.7)

        put_text(frame, "[N] Next  [P] Prev  [Z] Undo  [Q] Quit",
                 (w // 2 - 200, h - 25), color=(180, 180, 180), scale=0.55)

        if last_saved_label:
            put_text(frame, last_saved_label, (w - 280, 32),
                     color=(180, 255, 180), scale=0.55)

        cv2.imshow("Static Gesture Collector", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        elif key == ord(' '):
            if not hand_detected:
                print("  손이 감지되지 않아 저장 불가")
                continue
            save_dir = os.path.join(DATA_DIR, gesture)
            ensure_dir(save_dir)
            idx  = count_saved(gesture)
            path = os.path.join(save_dir, f"{idx:04d}.npy")
            np.save(path, features)
            print(f"  저장: {gesture} [{idx+1}/{SAMPLES_TARGET}]")
            last_saved_label = f"Saved: {gesture} #{idx+1}"
            flash_counter = 3

        elif key == ord('n'):
            gesture_idx = (gesture_idx + 1) % len(GESTURES)
            last_saved_label = ""

        elif key == ord('p'):
            gesture_idx = (gesture_idx - 1) % len(GESTURES)
            last_saved_label = ""

        elif key == ord('z'):
            if delete_last(gesture):
                print(f"  삭제: {gesture} 마지막 샘플")
                last_saved_label = f"Deleted: {gesture}"
            else:
                print(f"  삭제할 샘플 없음")

    cap.release()
    cv2.destroyAllWindows()

    # 수집 결과 요약
    print("\n=== 수집 결과 ===")
    total = 0
    for g in GESTURES:
        n = count_saved(g)
        total += n
        status = "✅" if n >= SAMPLES_TARGET else f"⚠ ({n}/{SAMPLES_TARGET})"
        print(f"  {g:12s}: {n:3d}개  {status}")
    print(f"\n  총 {total}개 샘플")
    print(f"  위치: {DATA_DIR}")
    print(f"\n다음 단계: python train_static.py")


if __name__ == "__main__":
    main()
