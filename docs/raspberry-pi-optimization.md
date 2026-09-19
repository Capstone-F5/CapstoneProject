# 라즈베리파이4 프론트엔드 최적화 분석

> 환경: 라즈베리파이4 (ARM Cortex-A72 1.8GHz × 4코어, 4GB RAM)  
> 역할: 서버는 별도 PC, 파이는 Chromium 브라우저로 프론트만 표시

---

## 현재 부하 요인

### 의존성 (package.json — 런타임 7개)

| 패키지 | 역할 | 무게 |
|---|---|---|
| `onnxruntime-web` ^1.18.0 | VAD·추론용 WASM 런타임 | **매우 무거움** — WASM 바이너리 수 MB + SharedArrayBuffer 멀티스레드 |
| `@mediapipe/hands` ^0.4 | 손동작 추적 | **매우 무거움** — 자체 WASM + `.task` 모델 파일 다운로드, 매 프레임 추론 |
| `@ricky0123/vad-react` ^0.0.22 | 음성 활동 감지 | **무거움** — 내부적으로 onnxruntime-web 사용, ONNX 모델 로드 |
| `@zxing/browser` + `@zxing/library` | QR 코드 스캔 | 중간 — 사용 시점에만 활성 |
| `react` + `react-dom` ^18.3.1 | UI | 경량 |

- **ML/AI 라이브러리 3종이 초기 번들에 모두 포함** (코드 스플리팅 없음)
- vite.config.js에 `rollupOptions.output.manualChunks` 설정 없음 → 단일 청크로 빌드됨

### 코드 복잡도

| 파일 | 라인 수 | Hook 호출 수 |
|---|---|---|
| `App.jsx` | 963줄 | **60회** (useState·useEffect·useCallback·useMemo·useRef) |
| `MenuScreen.jsx` | 757줄 | 17회 |
| 컴포넌트 | 9개 | — |
| Context | 1개 (GestureUIContext) | — |

- `App.jsx`가 단일 파일로 라우팅·제스처·음성·카메라·장바구니를 전부 처리
- 제스처 HUD 업데이트 등 잦은 리렌더 시 60개 훅이 모두 평가됨

### 이미지 에셋 (public/ 총 20MB)

| 파일 | 크기 | 문제 |
|---|---|---|
| `bg.png` | **1.8 MB** | PNG 원본, 미사용 가능성 (bg.jpg도 존재) |
| `더블치즈버거.png` | **824 KB** | PNG — 나머지는 전부 webp인데 이것만 미변환 |
| `logo.png` | 228 KB | 로고치고 과대 |
| 버거/세트 이미지 (webp) | 60–100 KB 각 | 적정 수준 |
| 총 이미지 파일 | **50개** | — |

### 카메라 / WebSocket (useApproachDetector)

- 항상 켜진 상태: 앱 시작과 동시에 카메라 스트림 + WebSocket 연결
- 2fps(500ms 간격), 320×240 JPEG 0.6 품질로 서버 전송 → 자체 부하는 낮음
- 단, `videoRef`·`canvasRef`를 매 프레임 DOM 없이 운용 → 메모리 해제 이슈 없음

---

## 라즈베리파이4 환경에서의 리스크

### 1순위 — WASM ML 런타임 (가장 심각)

ARM Cortex-A72의 단일 스레드 성능은 최신 데스크탑 대비 **약 35–45% 수준**.  
`onnxruntime-web` 1.18+은 threaded WASM(SharedArrayBuffer + Atomics)을 요구하는데,  
파이4에서 4코어를 전부 써도 추론 지연이 수백 ms → **제스처 인식 FPS 저하**, UI 버벅임 동시 발생.  
`@mediapipe/hands`는 매 프레임 Hand Landmark 추론(~21개 키포인트)을 수행 → CPU 점유 최대 50–80%.

### 2순위 — App.jsx 단일 거대 컴포넌트

60개 훅이 하나의 컴포넌트에 집중 → 제스처 HUD처럼 고빈도 상태 변경이 발생할 때  
React가 전체 App 트리를 재평가. 파이4의 낮은 JS 엔진 성능(V8 on ARM)에서 드롭 프레임 유발.

### 3순위 — 초기 번들 로드 시간

코드 스플리팅 없이 ML 라이브러리가 전부 포함된 번들을 파이4 Chromium이 파싱·컴파일.  
파이4 eMMC/SD 카드 I/O 속도에 따라 초기 로딩이 **10–20초** 이상 걸릴 수 있음.

### 4순위 — 대용량 PNG 에셋

`bg.png`(1.8MB)가 첫 화면에 로드되면 파이4 저대역 GPU(VideoCore VI)가 디코딩 부담.  
Chromium on ARM은 PNG를 CPU 디코딩하므로 렌더링 첫 프레임 지연 발생.

### 5순위 — 메모리 압박

`onnxruntime-web` WASM 힙 + MediaPipe 모델 + React 힙 합산 시 **1.5–2.5GB** 예상.  
파이4 4GB 중 OS·Chromium 기본 사용량(~800MB)을 합치면 여유가 빠듯함.

---

## 최적화 방안 (우선순위 순)

### ① ML 라이브러리 동적 import + 코드 스플리팅 ★★★

**현재 문제:** `@mediapipe/hands`, `onnxruntime-web`, `@ricky0123/vad-react`가 초기 번들에 포함되어 앱 진입 시 전부 로드됨.

**해결책:**
```js
// vite.config.js — manualChunks 추가
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'mediapipe': ['@mediapipe/hands'],
        'onnx':      ['onnxruntime-web'],
        'vad':       ['@ricky0123/vad-react'],
        'zxing':     ['@zxing/browser', '@zxing/library'],
      },
    },
  },
},
```
각 기능 훅(`useGesture`, `useVAD` 등)에서 `await import(...)` 형태로 지연 로드.

**예상 효과:** 초기 번들 파싱 시간 50–70% 감소, 첫 화면 표시까지 시간 단축.

---

### ② MediaPipe Hands → OffscreenCanvas + Worker 분리 ★★★

**현재 문제:** 손동작 추론이 메인 스레드에서 실행되어 React 렌더와 CPU를 공유.

**해결책:** `new Worker()`로 별도 스레드를 띄우고, `OffscreenCanvas`로 카메라 프레임을 Worker에 전달. 추론 결과만 `postMessage`로 메인 스레드에 반환.

```js
// gesture.worker.js (별도 파일)
import { Hands } from '@mediapipe/hands'
// 추론 후 self.postMessage({ landmarks })
```

**예상 효과:** 메인 스레드 CPU 점유 30–40% 감소, UI 프레임 드롭 해소.

---

### ③ App.jsx 분할 + React.memo / 상태 격리 ★★

**현재 문제:** 963줄 단일 컴포넌트, 60개 훅 → 고빈도 상태(제스처 HUD, 토스트) 업데이트 시 전체 트리 리렌더.

**해결책:**
- 제스처 HUD·토스트 알림을 별도 컴포넌트로 분리 + `React.memo` 적용
- 고빈도 상태(`gestureKey`, `voiceToast`)를 Context로 격리해 구독 컴포넌트만 리렌더
- 화면 전환 로직을 `useReducer`로 통합해 `useState` 난립 정리

**예상 효과:** 리렌더 횟수 감소, 파이4에서 애니메이션 버벅임 개선.

---

### ④ bg.png 제거 및 이미지 최적화 ★★

**현재 문제:**
- `bg.png` 1.8MB (bg.jpg 68KB와 중복 존재)
- `더블치즈버거.png` 824KB (다른 메뉴는 전부 webp 60–100KB)

**해결책:**
```bash
# bg.png 삭제 (bg.jpg로 대체)
rm frontend/public/bg.png

# PNG → WebP 변환
cwebp -q 82 frontend/public/images/burgers/더블치즈버거.png \
      -o frontend/public/images/burgers/더블치즈버거.webp

# logo.png 경량화 (228KB → 목표 30KB 이하)
cwebp -q 90 frontend/public/logo.png -o frontend/public/logo.webp
```
코드에서 `<img src="/logo.png">` → `/logo.webp`로 교체.

**예상 효과:** 초기 로드 데이터 ~2MB 감소, 첫 화면 렌더 속도 개선.

---

### ⑤ 접근 감지 카메라 조건부 활성화 ★★

**현재 문제:** `useApproachDetector`가 `enabled: true` 하드코딩으로 앱 시작 즉시 카메라 + WebSocket 점유.

**해결책:** 관리자 설정 또는 환경변수(`VITE_APPROACH_DETECT=true`)로 토글 가능하게 변경. 파이4 데모 환경에서 불필요 시 완전히 끌 수 있게.

```js
// App.jsx
const approachEnabled = import.meta.env.VITE_APPROACH_DETECT !== 'false'
const { notifyUserInput } = useApproachDetector({
  enabled: approachEnabled,
  ...
})
```

**예상 효과:** 비활성 시 카메라 스트림 + WebSocket CPU·메모리 절약.

---

### ⑥ Vite 빌드 압축 + 사전 캐시 설정 ★

**현재 문제:** 빌드 설정에 압축(`vite-plugin-compression`) 없음 → 파이4가 큰 JS 파일을 매 시작마다 파싱.

**해결책:**
```bash
npm install -D vite-plugin-compression
```
```js
// vite.config.js
import compression from 'vite-plugin-compression'
plugins: [react(), compression({ algorithm: 'brotliCompress' })]
```
Nginx/Caddy에서 `Content-Encoding: br` 응답 설정.

**예상 효과:** 전송 번들 크기 60–70% 감소, 파이4 Chromium 네트워크 수신 시간 단축.

---

### ⑦ onnxruntime-web WASM 스레드 수 제한 ★

**현재 문제:** 기본값으로 논리 코어 수(4) 만큼 WASM 스레드를 생성 → OS + Chromium + React와 코어 경쟁.

**해결책:** 파이4 환경에서는 스레드 2개로 제한.

```js
import * as ort from 'onnxruntime-web'
ort.env.wasm.numThreads = 2
```

**예상 효과:** UI 렌더에 코어 2개 확보, 체감 반응 속도 개선.

---

## 요약 우선순위표

| 순위 | 방안 | 난이도 | 예상 효과 |
|---|---|---|---|
| 1 | ML 라이브러리 코드 스플리팅 | 중 | 초기 로딩 50–70% 단축 |
| 2 | MediaPipe → Web Worker 분리 | 높음 | 메인 스레드 CPU 30–40% 절감 |
| 3 | App.jsx 분할 + 상태 격리 | 중 | 리렌더 감소, 애니메이션 개선 |
| 4 | bg.png 제거 + PNG→WebP | 낮음 | 에셋 2MB+ 감소 |
| 5 | 접근 감지 조건부 활성화 | 낮음 | 불필요 리소스 점유 해제 |
| 6 | Brotli 압축 빌드 | 낮음 | 번들 전송 60% 감소 |
| 7 | WASM 스레드 수 제한 | 낮음 | UI 코어 여유 확보 |
