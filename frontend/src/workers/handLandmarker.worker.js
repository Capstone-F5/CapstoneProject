// MediaPipe HandLandmarker를 메인 스레드 밖에서 돌리는 워커.
// 메인 스레드는 카메라 프레임(ImageBitmap)만 넘기고, 랜드마크 결과만 돌려받는다.
// 모듈 워커에서는 importScripts를 쓸 수 없으므로 forVisionTasks(…, useModule=true)로
// ES 모듈 형태의 wasm 로더를 받는다 (vite.config.js의 worker.format: 'es'와 짝).
import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision'

// tasks-vision은 모듈 워커에서 wasm 로더를 self.import(url) → import(url) 순으로 불러온다.
// 번들된 코드 안의 import(url)은 Vite 개발 서버가 public 파일에 '?import'를 붙여 깨뜨리므로,
// Vite 변환을 거치지 않는 네이티브 dynamic import를 직접 제공한다.
self.import = new Function('url', 'return import(url)')

let landmarker = null

console.info('[worker] loaded')

self.onmessage = async (e) => {
  const msg = e.data

  if (msg.type === 'init') {
    try {
      const t0 = performance.now()
      const fileset = await FilesetResolver.forVisionTasks(msg.wasmBase, true)
      console.info(`[worker] fileset ${Math.round(performance.now() - t0)}ms`)
      landmarker = await HandLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: msg.modelPath, delegate: msg.delegate },
        runningMode: 'VIDEO',
        numHands: msg.numHands,
        minHandDetectionConfidence: msg.minDetectionConfidence,
        minHandPresenceConfidence:  msg.minPresenceConfidence,
        minTrackingConfidence:      msg.minTrackingConfidence,
      })
      console.info(`[worker] landmarker ready ${Math.round(performance.now() - t0)}ms`)
      self.postMessage({ type: 'ready' })
    } catch (err) {
      console.error('[worker] init failed', err)
      self.postMessage({ type: 'error', message: String(err?.message ?? err) })
    }
    return
  }

  if (msg.type === 'frame') {
    try {
      const started = performance.now()
      const r = landmarker.detectForVideo(msg.bitmap, msg.ts)
      self.postMessage({
        type: 'result',
        landmarks: r.landmarks,
        // legacy @mediapipe/hands의 multiHandedness와 같은 형태({label}) — 라벨 규칙도 동일(미러 입력 가정)
        handedness: r.handedness.map(h => ({ label: h[0]?.categoryName, score: h[0]?.score })),
        inferMs: performance.now() - started,
      })
    } catch (err) {
      self.postMessage({ type: 'frameError', message: String(err?.message ?? err) })
    } finally {
      msg.bitmap.close()
    }
    return
  }

  if (msg.type === 'close') {
    try { landmarker?.close() } catch {}
    landmarker = null
    self.close()
  }
}
