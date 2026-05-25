"""
Dynamic gesture (swipe) classifier training

Features:
    - Relative wrist trajectory  (SEQ_LEN x 2)  - position relative to start
    - Frame-to-frame velocity    ((SEQ_LEN-1) x 2)
    Total: SEQ_LEN*2 + (SEQ_LEN-1)*2  =  (2*SEQ_LEN - 1) * 2  features

Augmentation (training only):
    - Mirror x-axis: swipe_left <-> swipe_right (label swap)
    - Gaussian noise on positions
    - Time stretch x0.8 / x1.2 (resample to SEQ_LEN)
"""

import os
import numpy as np
import joblib
from collections import Counter
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix

SEQ_LEN    = 20
DATA_DIR   = os.path.join(os.path.dirname(__file__), 'data_dynamic')
MODEL_DIR  = os.path.join(os.path.dirname(__file__), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'dynamic_mlp.pkl')

NOISE_SIGMA = 0.008
RNG = np.random.default_rng(42)

# Mirror augmentation swaps these labels
_MIRROR_SWAP = {'swipe_left': 'swipe_right', 'swipe_right': 'swipe_left'}


# ── Feature extraction ────────────────────────────────────────────────────────

def resample(seq, target_len):
    """Resample sequence to target_len via linear interpolation"""
    n = len(seq)
    if n == target_len:
        return np.array(seq, dtype=np.float32)
    old_t = np.linspace(0, 1, n)
    new_t = np.linspace(0, 1, target_len)
    return np.stack(
        [np.interp(new_t, old_t, np.array(seq)[:, d]) for d in range(2)],
        axis=-1
    ).astype(np.float32)


def extract_features(seq):
    """
    seq: array-like (SEQ_LEN, 2) wrist xy in MediaPipe coords (0~1)
    Returns 1-D feature vector

    Features:
        - relative trajectory  (SEQ_LEN x 2)
        - frame velocity       ((SEQ_LEN-1) x 2)
        - summary (8):
            net_dx, net_dy          — 최종 이동 방향·크기
            x_dominance             — 0=수직, 1=수평 (up/down vs left/right 구분)
            net_dx_signed_norm,     — 부호 있는 수평 비율 (left vs right)
            net_dy_signed_norm      — 부호 있는 수직 비율 (up vs down)
            max_speed               — 최대 순간 속도
            path_straightness       — 1=직선, 0=곡선 (스와이프 품질)
            mid_displacement        — 중간 지점 이동 거리 (가속도 프로파일)
    """
    seq = resample(seq, SEQ_LEN)
    rel = seq - seq[0]
    vel = np.diff(rel, axis=0)

    net        = rel[-1]                                    # (2,) 최종 이동
    abs_net    = np.abs(net)
    abs_sum    = abs_net.sum() + 1e-6
    x_dom      = float(abs_net[0] / abs_sum)               # 0~1, 1=수평
    net_x_norm = float(net[0] / abs_sum)                   # 부호 있는 수평 비율
    net_y_norm = float(net[1] / abs_sum)                   # 부호 있는 수직 비율
    speeds     = np.linalg.norm(vel, axis=1)
    max_speed  = float(speeds.max())
    path_len   = float(speeds.sum()) + 1e-6
    straight   = float(np.linalg.norm(net) / path_len)
    mid_disp   = float(np.linalg.norm(rel[SEQ_LEN // 2]))  # 중간 지점 누적 이동

    summary = np.array([
        net[0], net[1],
        x_dom, net_x_norm, net_y_norm,
        max_speed, straight, mid_disp,
    ], dtype=np.float32)

    return np.concatenate([rel.flatten(), vel.flatten(), summary])


# ── Augmentation ──────────────────────────────────────────────────────────────

def augment_one(seq, label):
    """Returns list of (seq, label) including original"""
    seq = resample(seq, SEQ_LEN)
    results = [(seq, label)]

    # 1. Mirror x → swap left/right labels
    mir = seq.copy()
    mir[:, 0] = 1.0 - mir[:, 0]
    results.append((mir, _MIRROR_SWAP.get(label, label)))

    # 2. Gaussian noise
    noisy = seq + RNG.normal(0, NOISE_SIGMA, seq.shape).astype(np.float32)
    results.append((noisy, label))

    # 3. Noise on mirror
    noisy_mir = mir + RNG.normal(0, NOISE_SIGMA, mir.shape).astype(np.float32)
    results.append((noisy_mir, _MIRROR_SWAP.get(label, label)))

    # 4-5. Time stretch x0.8 / x1.2 (simulate faster / slower swipes)
    # src_t must match seq length; resample to n_frames, then back to SEQ_LEN
    for factor in (0.8, 1.2):
        n_frames = max(3, int(SEQ_LEN * factor))
        src_t    = np.linspace(0, 1, SEQ_LEN)   # matches seq length
        dst_t    = np.linspace(0, 1, n_frames)
        mid = np.stack(
            [np.interp(dst_t, src_t, seq[:, d]) for d in range(2)],
            axis=-1
        ).astype(np.float32)
        results.append((resample(mid, SEQ_LEN), label))

    return results


# ── Data loading ──────────────────────────────────────────────────────────────

def load_dataset():
    if not os.path.exists(DATA_DIR):
        print(f"Data directory not found: {DATA_DIR}")
        return None, None, None

    classes = sorted([
        c for c in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, c))
    ])

    X, y = [], []
    for cls in classes:
        cls_dir = os.path.join(DATA_DIR, cls)
        files   = [f for f in os.listdir(cls_dir) if f.endswith('.npy')]
        for fname in files:
            arr = np.load(os.path.join(cls_dir, fname))
            if arr.ndim != 2 or arr.shape[1] != 2:
                print(f"  Skip (bad shape): {fname} {arr.shape}")
                continue
            X.append(arr)
            y.append(cls)

    if not X:
        print("No training data found. Run collect_dynamic.py first.")
        return None, None, None

    return X, np.array(y), classes


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Dynamic Gesture Classifier Training ===\n")

    X_raw, y, classes = load_dataset()
    if X_raw is None:
        return

    print(f"Classes: {classes}")
    print("Sample distribution (raw):")
    for cls, cnt in sorted(Counter(y).items()):
        print(f"  {cls:14s}: {cnt:3d}")
    print(f"Total: {len(X_raw)} raw samples, feature dim: {len(extract_features(X_raw[0]))}\n")

    le    = LabelEncoder()
    y_enc = le.fit_transform(y)
    classes = list(le.classes_)

    # Split on raw indices (validation uses original, unaugmented sequences)
    indices = np.arange(len(X_raw))
    idx_tr, idx_te = train_test_split(
        indices, test_size=0.2, random_state=42, stratify=y_enc
    )

    X_te = np.array([extract_features(X_raw[i]) for i in idx_te])
    y_te = y_enc[idx_te]

    # Augment training set only
    X_tr_aug, y_tr_aug = [], []
    for i in idx_tr:
        raw_label = le.inverse_transform([y_enc[i]])[0]
        for seq_aug, label_aug in augment_one(X_raw[i], raw_label):
            X_tr_aug.append(extract_features(seq_aug))
            y_tr_aug.append(le.transform([label_aug])[0])

    X_tr_aug = np.array(X_tr_aug)
    y_tr_aug = np.array(y_tr_aug)

    print(f"Split — train: {len(idx_tr)} raw  ->  {len(X_tr_aug)} augmented,  "
          f"val: {len(idx_te)} raw")

    # Model
    model = Pipeline([
        ('scaler', StandardScaler()),
        ('mlp', MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=25,
        )),
    ])

    print("Training...")
    model.fit(X_tr_aug, y_tr_aug)
    print(f"Done. Epochs: {model.named_steps['mlp'].n_iter_}\n")

    # Evaluation
    y_pred_enc = model.predict(X_te)
    y_pred_str = le.inverse_transform(y_pred_enc)
    y_te_str   = le.inverse_transform(y_te)
    train_acc  = model.score(X_tr_aug, y_tr_aug)
    test_acc   = model.score(X_te, y_te)

    print("=== Performance ===")
    print(f"Train accuracy (augmented): {train_acc:.3f}")
    print(f"Val accuracy   (raw only) : {test_acc:.3f}\n")

    print("=== Per-class ===")
    print(classification_report(y_te_str, y_pred_str, digits=3))

    print("=== Confusion Matrix ===")
    cm = confusion_matrix(y_te_str, y_pred_str, labels=classes)
    header = " " * 16 + " ".join(f"{c[:10]:>11s}" for c in classes)
    print(header)
    for i, cls in enumerate(classes):
        row = f"  {cls[:14]:14s} " + " ".join(f"{v:>11d}" for v in cm[i])
        print(row)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({'model': model, 'classes': classes, 'seq_len': SEQ_LEN}, MODEL_PATH)
    print(f"\nModel saved: {MODEL_PATH}")


if __name__ == "__main__":
    main()
