"""
정적 제스처 분류기 학습 (sklearn MLP + 데이터 증강)

사용법:
    python train_static.py

데이터 증강 (학습 데이터에만 적용):
    - Mirror (좌우 반전)         → 왼손/오른손 보강
    - Rotate z ±12° (in-plane)   → 손목 회전 보강
    - Rotate y ±8° (tilt)        → 손등/손바닥 각도 보강
    - Gaussian noise σ=0.015     → 미세 진동 강인성

기본: 원본 1개 → 6개
ok/none: 원본 1개 → 10개 (핀치 경계 강화용 추가 증강)
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

DATA_DIR   = os.path.join(os.path.dirname(__file__), 'data_static')
MODEL_DIR  = os.path.join(os.path.dirname(__file__), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'static_mlp.pkl')

# ── 증강 파라미터 ────────────────────────────────────────────────────────────
ROT_Z_RANGE = 12.0   # 도 단위, z축 회전 (in-plane)
ROT_Y_RANGE = 8.0    # 도 단위, y축 회전 (tilt)
NOISE_SIGMA = 0.015  # 정규화 좌표 기준 노이즈 표준편차

RNG = np.random.default_rng(42)


# ── 증강 함수들 ──────────────────────────────────────────────────────────────

def _mirror_x(coords):
    """좌우 반전 (x값 부호 반전)"""
    out = coords.copy()
    out[:, 0] = -out[:, 0]
    return out


def _rotate_z(coords, deg):
    """z축 기준 회전 (in-plane, 손목 회전)"""
    r = np.radians(deg)
    c, s = np.cos(r), np.sin(r)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return coords @ R.T


def _rotate_y(coords, deg):
    """y축 기준 회전 (tilt, 손등/손바닥)"""
    r = np.radians(deg)
    c, s = np.cos(r), np.sin(r)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return coords @ R.T


# ok/none 는 핀치 경계 혼동이 크므로 추가 증강 적용
HEAVY_AUG_CLASSES = {'ok', 'none'}


def augment_one(features, heavy=False):
    """원본 1개 → 6개(기본) or 10개(heavy) 버전"""
    coords   = features.reshape(21, 3)
    out      = [features.copy()]

    # 1. Mirror
    mirrored = _mirror_x(coords)
    out.append(mirrored.flatten())

    # 2-3. Random rotation (z + y)
    for _ in range(2):
        rz = RNG.uniform(-ROT_Z_RANGE, ROT_Z_RANGE)
        ry = RNG.uniform(-ROT_Y_RANGE, ROT_Y_RANGE)
        rotated = _rotate_y(_rotate_z(coords, rz), ry)
        out.append(rotated.flatten())

    # 4. Mirror + rotation
    rz = RNG.uniform(-ROT_Z_RANGE, ROT_Z_RANGE)
    ry = RNG.uniform(-ROT_Y_RANGE, ROT_Y_RANGE)
    mr = _rotate_y(_rotate_z(mirrored, rz), ry)
    out.append(mr.flatten())

    # 5. Noise
    noisy = coords + RNG.normal(0, NOISE_SIGMA, coords.shape)
    out.append(noisy.flatten())

    if heavy:
        # 6-7. 강한 노이즈 (σ×2)
        for _ in range(2):
            out.append((coords + RNG.normal(0, NOISE_SIGMA * 2, coords.shape)).flatten())
        # 8. Mirror + 강한 노이즈
        out.append((mirrored + RNG.normal(0, NOISE_SIGMA * 1.5, coords.shape)).flatten())
        # 9. 다른 회전 각도 조합
        rz = RNG.uniform(-ROT_Z_RANGE * 1.5, ROT_Z_RANGE * 1.5)
        ry = RNG.uniform(-ROT_Y_RANGE * 1.5, ROT_Y_RANGE * 1.5)
        out.append(_rotate_y(_rotate_z(coords, rz), ry).flatten())

    return out


def augment_dataset(X, y, classes):
    """학습 데이터셋 전체 증강 — ok/none는 heavy 적용"""
    label_names = np.array(classes)
    X_out, y_out = [], []
    for features, label_idx in zip(X, y):
        cls_name = label_names[label_idx]
        heavy    = cls_name in HEAVY_AUG_CLASSES
        versions = augment_one(features, heavy=heavy)
        X_out.extend(versions)
        y_out.extend([label_idx] * len(versions))
    return np.array(X_out), np.array(y_out)


# ── 데이터 로드 ──────────────────────────────────────────────────────────────

def load_dataset():
    X, y = [], []
    if not os.path.exists(DATA_DIR):
        print(f"❌ 데이터 폴더 없음: {DATA_DIR}")
        return None, None, None

    classes = sorted(os.listdir(DATA_DIR))
    classes = [c for c in classes if os.path.isdir(os.path.join(DATA_DIR, c))]

    for cls in classes:
        cls_dir = os.path.join(DATA_DIR, cls)
        files   = [f for f in os.listdir(cls_dir) if f.endswith('.npy')]
        for f in files:
            arr = np.load(os.path.join(cls_dir, f))
            if arr.shape != (63,):
                print(f"  ⚠ 잘못된 shape 무시: {f} {arr.shape}")
                continue
            X.append(arr)
            y.append(cls)

    if not X:
        print("❌ 학습 데이터가 비어 있습니다. 먼저 collect_static.py 를 실행하세요.")
        return None, None, None

    return np.array(X), np.array(y), classes


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    print("=== 정적 제스처 분류기 학습 (데이터 증강 포함) ===\n")

    X, y, classes = load_dataset()
    if X is None:
        return

    print(f"클래스: {classes}")
    print(f"원본 샘플 분포:")
    for cls, cnt in sorted(Counter(y).items()):
        print(f"  {cls:12s}: {cnt:3d}개")
    print(f"총 {len(X)}개 원본 샘플, 특징 차원 {X.shape[1]}\n")

    # ── 라벨 인코딩 ────────────────────────────────────────────────────────
    le        = LabelEncoder()
    y_encoded = le.fit_transform(y)
    classes   = list(le.classes_)

    # ── 학습/검증 분할 (원본 기준) ──────────────────────────────────────────
    # 검증은 원본만 사용 → 정직한 성능 평가
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    print(f"원본 분할 — 학습용: {len(X_train)}개, 검증용: {len(X_test)}개")

    # ── 학습 데이터만 증강 ──────────────────────────────────────────────────
    X_train_aug, y_train_aug = augment_dataset(X_train, y_train, classes)
    print(f"증강 후 — 학습용: {len(X_train_aug)}개 (×{len(X_train_aug)//len(X_train)} 배)\n")

    # ── 모델 정의 ──────────────────────────────────────────────────────────
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

    print("학습 중...")
    model.fit(X_train_aug, y_train_aug)
    print(f"학습 완료. epoch: {model.named_steps['mlp'].n_iter_}\n")

    # ── 평가 (원본 검증 세트) ──────────────────────────────────────────────
    y_pred_enc = model.predict(X_test)
    y_pred_str = le.inverse_transform(y_pred_enc)
    y_test_str = le.inverse_transform(y_test)
    train_acc  = model.score(X_train_aug, y_train_aug)
    test_acc   = model.score(X_test, y_test)

    print("=== 성능 ===")
    print(f"학습 정확도 (증강 포함): {train_acc:.3f}")
    print(f"검증 정확도 (원본만)   : {test_acc:.3f}\n")

    print("=== 클래스별 성능 ===")
    print(classification_report(y_test_str, y_pred_str, digits=3))

    print("=== Confusion Matrix ===")
    cm = confusion_matrix(y_test_str, y_pred_str, labels=classes)
    header = " " * 12 + " ".join(f"{c[:8]:>9s}" for c in classes)
    print(header)
    for i, cls in enumerate(classes):
        row = f"  {cls[:10]:10s} " + " ".join(f"{v:>9d}" for v in cm[i])
        print(row)

    # ── 저장 ───────────────────────────────────────────────────────────────
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({
        'model':   model,
        'classes': classes,
    }, MODEL_PATH)
    print(f"\n✅ 모델 저장: {MODEL_PATH}")


if __name__ == "__main__":
    main()
