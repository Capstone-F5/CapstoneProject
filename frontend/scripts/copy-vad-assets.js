/**
 * Silero VAD 실행에 필요한 ONNX 모델 및 WASM 파일을 public/ 으로 복사.
 * npm install 후 자동 실행 (postinstall) 또는 수동 실행 (npm run copy-vad).
 */
import { cpSync, existsSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root      = resolve(__dirname, '..')
const publicDir = resolve(root, 'public')

if (!existsSync(publicDir)) mkdirSync(publicDir, { recursive: true })

const assets = [
  // Silero VAD 모델 (ONNX)
  {
    src: resolve(root, 'node_modules/@ricky0123/vad-web/dist/silero_vad.onnx'),
    dst: resolve(publicDir, 'silero_vad.onnx'),
  },
  // AudioWorklet 번들
  {
    src: resolve(root, 'node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js'),
    dst: resolve(publicDir, 'vad.worklet.bundle.min.js'),
  },
  // ONNX Runtime WASM (단일 스레드 — SharedArrayBuffer 불필요)
  {
    src: resolve(root, 'node_modules/onnxruntime-web/dist/ort-wasm-simd.wasm'),
    dst: resolve(publicDir, 'ort-wasm-simd.wasm'),
  },
  // ONNX Runtime WASM (멀티 스레드 — COOP/COEP 헤더 있을 때 자동 선택)
  {
    src: resolve(root, 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm'),
    dst: resolve(publicDir, 'ort-wasm-simd-threaded.wasm'),
  },
]

let copied = 0
for (const { src, dst } of assets) {
  if (!existsSync(src)) {
    console.warn(`[copy-vad] 건너뜀 (없음): ${src}`)
    continue
  }
  cpSync(src, dst)
  console.log(`[copy-vad] 복사: ${src.split('node_modules')[1]} → public/`)
  copied++
}

if (copied === 0) {
  console.warn('[copy-vad] 복사된 파일 없음. npm install 이 완료됐는지 확인하세요.')
} else {
  console.log(`[copy-vad] 완료 (${copied}/${assets.length}개)`)
}
