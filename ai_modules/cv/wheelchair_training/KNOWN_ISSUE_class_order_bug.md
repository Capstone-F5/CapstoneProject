# 발견된 버그 (이번 작업 범위 밖 — 별도 확인 필요)

`ai_modules/cv/approach_detector.py`의 `WHITE_CANE_CLASS_ID = 1`이 실제 모델 클래스 순서와 반대인 것으로 보입니다.

## 근거

`visionguide_dataset/datasets/train`의 정답 라벨(`white_cane=0, person=1`, data.yaml 기준)과
`best_int8.tflite`의 실제 출력을 626개(person) / 190개(white_cane) 정답 박스 위치에서 통계적으로 대조한 결과:

- white_cane 정답 위치 → 모델 **class0** 평균 confidence 0.350, class1은 0.000
- person 정답 위치 → 모델 **class1** 평균 confidence 0.420, class0은 0.000

즉 **class0 = white_cane, class1 = person**이 맞고, 현재 `WHITE_CANE_CLASS_ID = 1`은 반대로 설정되어 있습니다.
이대로면 프로덕션 흰 지팡이 접근 감지 기능이 실제로는 "사람이 감지되면 흰 지팡이로 판정"하는 식으로 오작동할 가능성이 있습니다.

재현/검증 스크립트: `ai_modules/cv/wheelchair_training/scripts/debug_class_order.py`

## 상태

- 2026-09-14 확인, 사용자 요청으로 이번 작업(휠체어 클래스 추가 학습/양자화)에서는 수정하지 않고 별도 이슈로 남겨둠.
- 재학습 시 `person=0, white_cane=1, wheelchair=2`로 클래스 순서를 명시적으로 재설계하므로, 새 모델이 배포되면 이 버그는 자연히 해소될 수 있음 (단, 배포 전까지는 기존 `best_int8.tflite`를 쓰는 프로덕션에 버그가 남아있음).
