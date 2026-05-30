"""
Dynamic gesture (swipe) data collection

Controls:
    SPACE   - Start recording (auto-saves after SEQ_LEN frames)
    N       - Next gesture
    P       - Previous gesture
    Z       - Undo last sample (or cancel current recording)
    Q       - Quit

Tips:
    - Perform the full swipe within ~1 second after pressing SPACE
    - Keep hand open (fingers spread) during swipe
    - none: small random hand movement, holding still, entering/leaving frame
    - Vary starting position and swipe distance

Save format:
    data_dynamic/<gesture>/<index>.npy  shape: (SEQ_LEN, 2)  - wrist xy (MediaPipe 0~1)
"""

import cv2
import mediapipe as mp
import numpy as np
import os

GESTURES = [
    'none',
    'swipe_left',
    'swipe_right',
    'swipe_up',
    'swipe_down',
]

SEQ_LEN        = 20   # frames per sequence (~0.8s at 25fps)
SAMPLES_TARGET = 60
DATA_DIR       = os.path.join(os.path.dirname(__file__), 'data_dynamic')

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)


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
                if ret and frame is not None and float(frame.std()) > 5.0:
                    print(f"Camera: index={idx}, backend={name}")
                    return cap
            cap.release()
    return None


def draw_trail(frame, traj):
    """Visualize recorded wrist trajectory"""
    h, w, _ = frame.shape
    pts = [(int(x * w), int(y * h)) for x, y in traj]
    for i in range(1, len(pts)):
        alpha = i / len(pts)
        color = (int(50 * alpha), int(50 + 200 * alpha), int(255 * alpha))
        cv2.line(frame, pts[i-1], pts[i], color, 3)
    if pts:
        cv2.circle(frame, pts[-1], 7, (0, 255, 255), -1)


def main():
    print("\nCamera connecting...")
    cap = open_camera()
    if cap is None:
        print("Camera open failed.")
        return

    gesture_idx   = 0
    recording     = False
    seq_buffer    = []
    flash_counter = 0
    last_status   = ""

    print("=== Dynamic Gesture Collector ===")
    print(f"SEQ_LEN={SEQ_LEN} frames per sample, target={SAMPLES_TARGET} per class")
    print("SPACE=Record  N=Next  P=Prev  Z=Undo/Cancel  Q=Quit\n")

    fail_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            fail_count += 1
            if fail_count > 30:
                break
            continue
        fail_count = 0

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        hand_detected = False
        wrist_xy = None

        if result.multi_hand_landmarks:
            hand_detected = True
            lm = result.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)
            # Palm center: average of 4 MCP joints (손목 고정 스와이프에도 대응)
            _mcps = [5, 9, 13, 17]
            wrist_xy = (
                sum(lm.landmark[i].x for i in _mcps) / 4,
                sum(lm.landmark[i].y for i in _mcps) / 4,
            )

        # Append to buffer while recording
        if recording:
            pt = wrist_xy if (hand_detected and wrist_xy) else (0.5, 0.5)
            seq_buffer.append(pt)

            if len(seq_buffer) >= SEQ_LEN:
                gesture  = GESTURES[gesture_idx]
                save_dir = os.path.join(DATA_DIR, gesture)
                ensure_dir(save_dir)
                idx_n = count_saved(gesture)
                path  = os.path.join(save_dir, f"{idx_n:04d}.npy")
                arr   = np.array(seq_buffer[:SEQ_LEN], dtype=np.float32)
                np.save(path, arr)
                print(f"  Saved: {gesture} [{idx_n+1}/{SAMPLES_TARGET}]")
                last_status   = f"Saved: {gesture} #{idx_n+1}"
                flash_counter = 6
                recording     = False
                seq_buffer    = []

        # Draw trail during recording
        if recording and len(seq_buffer) > 1:
            draw_trail(frame, seq_buffer)

        # Green border flash after save
        if flash_counter > 0:
            cv2.rectangle(frame, (0, 0), (w, h), (0, 255, 0), 12)
            flash_counter -= 1

        gesture = GESTURES[gesture_idx]
        saved   = count_saved(gesture)

        # Top panel
        cv2.rectangle(frame, (0, 0), (w, 95), (30, 30, 30), -1)
        put_text(frame, f"[{gesture_idx+1}/{len(GESTURES)}] Gesture: {gesture}",
                 (10, 32), color=(100, 220, 255), scale=0.9)
        progress_color = (100, 255, 100) if saved >= SAMPLES_TARGET else (255, 200, 100)
        put_text(frame, f"Saved: {saved} / {SAMPLES_TARGET}",
                 (10, 65), color=progress_color, scale=0.7)
        bar_w = int((w - 220) * min(saved / SAMPLES_TARGET, 1.0))
        cv2.rectangle(frame, (210, 51), (210 + bar_w, 73), progress_color, -1)
        cv2.rectangle(frame, (210, 51), (w - 10, 73), (100, 100, 100), 1)

        # Bottom panel
        cv2.rectangle(frame, (0, h - 65), (w, h), (30, 30, 30), -1)
        if recording:
            prog = len(seq_buffer)
            put_text(frame, f"RECORDING  {prog} / {SEQ_LEN}",
                     (10, h - 35), color=(80, 80, 255), scale=0.8)
            bar_w2 = int((w - 20) * prog / SEQ_LEN)
            cv2.rectangle(frame, (10, h - 16), (10 + bar_w2, h - 6), (80, 80, 255), -1)
        elif hand_detected:
            put_text(frame, "Press SPACE to record  (perform swipe after pressing)",
                     (10, h - 35), color=(100, 255, 100), scale=0.6)
        else:
            put_text(frame, "Hand not detected", (10, h - 35), color=(100, 100, 255), scale=0.7)

        put_text(frame, "[N] Next  [P] Prev  [Z] Undo/Cancel  [Q] Quit",
                 (w // 2 - 220, h - 10), color=(160, 160, 160), scale=0.5)

        if last_status:
            put_text(frame, last_status, (w - 320, 32), color=(180, 255, 180), scale=0.55)

        cv2.imshow("Dynamic Gesture Collector", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' '):
            if not recording:
                recording  = True
                seq_buffer = []
                print(f"  Recording: {gesture}  (perform gesture now!)")
        elif key == ord('n'):
            gesture_idx = (gesture_idx + 1) % len(GESTURES)
            recording   = False
            seq_buffer  = []
            last_status = ""
        elif key == ord('p'):
            gesture_idx = (gesture_idx - 1) % len(GESTURES)
            recording   = False
            seq_buffer  = []
            last_status = ""
        elif key == ord('z'):
            if recording:
                recording  = False
                seq_buffer = []
                print("  Cancelled.")
            elif delete_last(gesture):
                print(f"  Deleted last: {gesture}")
                last_status = f"Deleted: {gesture}"
            else:
                print("  Nothing to delete.")

    cap.release()
    cv2.destroyAllWindows()

    print("\n=== Collection Summary ===")
    total = 0
    for g in GESTURES:
        n = count_saved(g)
        total += n
        status = "OK" if n >= SAMPLES_TARGET else f"({n}/{SAMPLES_TARGET})"
        print(f"  {g:14s}: {n:3d}  {status}")
    print(f"\n  Total: {total} samples")
    print(f"  Location: {DATA_DIR}")
    print("\nNext step: python train_dynamic.py")


if __name__ == "__main__":
    main()
