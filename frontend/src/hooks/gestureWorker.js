/* gestureWorker.js — MediaPipe Hands를 Worker 스레드에서 실행 */

const MP_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/'

let hands = null
let offscreen = null
let ctx = null
let ready = false

async function init() {
  const { Hands } = await import('@mediapipe/hands')
  hands = new Hands({ locateFile: (f) => `${MP_BASE}${f}` })
  hands.setOptions({
    maxNumHands:            1,
    modelComplexity:        0,
    minDetectionConfidence: 0.7,
    minTrackingConfidence:  0.5,
  })
  hands.onResults((results) => {
    self.postMessage({
      multiHandLandmarks: results.multiHandLandmarks ?? [],
      multiHandedness:    results.multiHandedness    ?? [],
    })
  })

  offscreen = new OffscreenCanvas(1, 1)
  ctx = offscreen.getContext('2d')
  ready = true
  self.postMessage({ type: 'ready' })
}

self.onmessage = async (e) => {
  const { bitmap, width, height } = e.data
  if (!bitmap) return

  if (!ready) {
    bitmap.close()
    return
  }

  if (offscreen.width !== width || offscreen.height !== height) {
    offscreen.width  = width
    offscreen.height = height
  }

  ctx.drawImage(bitmap, 0, 0)
  bitmap.close()

  try {
    await hands.send({ image: offscreen })
  } catch (err) {
    console.warn('[gestureWorker] hands.send 오류:', err)
  }
}

init().catch((err) => {
  console.error('[gestureWorker] 초기화 실패:', err)
})
