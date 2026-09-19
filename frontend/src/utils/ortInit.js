// 라즈베리파이4 환경에서 onnxruntime-web WASM 스레드 수를 제한한다.
// 기본값(논리 코어 수 = 4)은 OS·Chromium·React와 코어를 경쟁하므로
// UI에 코어 2개를 남겨두기 위해 추론 스레드를 2개로 고정한다.
// 이 파일은 vad-react/onnxruntime-web 이 처음 로드되기 전에 import 되어야 한다.
import * as ort from 'onnxruntime-web'

const maxThreads = Number(import.meta.env.VITE_ORT_THREADS ?? 2)
ort.env.wasm.numThreads = maxThreads
