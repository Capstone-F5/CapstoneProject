import { useEffect, useRef } from 'react'
import { Hands } from '@mediapipe/hands'

// ── WebSocket ────────────────────────────────────────────────────────────────
const _proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${_proto}//${window.location.host}/ws/gesture`

// ── 카메라 설정 ──────────────────────────────────────────────────────────────
const CAM_W   = 640
const CAM_H   = 480
const MAX_FPS = 30

const MP_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/'

const CAM_RETRY_COUNT = 4
const CAM_RETRY_DELAY = 1500

// ── 포인터 스무딩 파라미터 (서버측과 동일 — 둘 다 튜닝 가능) ─────────────────
const POINTER_MIN_CUTOFF = 0.15   // Hz — 정지 시 cutoff (낮을수록 떨림 ↓)
const POINTER_BETA       = 50.0   // 빠른 동작 반응성
const POINTER_D_CUTOFF   = 1.0
const POINTER_DEADZONE   = 0.0018 // 정규화 좌표 (이하 변화는 무시)

// ── One Euro Filter (Casiez et al. 2012) ────────────────────────────────────
class OneEuro {
  constructor(minCutoff, beta, dCutoff) {
    this.minCutoff = minCutoff
    this.beta      = beta
    this.dCutoff   = dCutoff
    this.xPrev  = null
    this.dxPrev = 0
    this.tPrev  = null
  }
  reset() {
    this.xPrev  = null
    this.dxPrev = 0
    this.tPrev  = null
  }
  filter(x, t) {
    if (this.xPrev === null) {
      this.xPrev = x
      this.tPrev = t
      return x
    }
    const dt = Math.max(t - this.tPrev, 1e-6)
    const dx = (x - this.xPrev) / dt
    const aD = lpfAlpha(this.dCutoff, dt)
    const dxHat = aD * dx + (1 - aD) * this.dxPrev
    const cutoff = this.minCutoff + this.beta * Math.abs(dxHat)
    const a = lpfAlpha(cutoff, dt)
    const xHat = a * x + (1 - a) * this.xPrev
    this.xPrev  = xHat
    this.dxPrev = dxHat
    this.tPrev  = t
    return xHat
  }
}

function lpfAlpha(cutoff, dt) {
  const tau = 1.0 / (2.0 * Math.PI * cutoff)
  return 1.0 / (1.0 + tau / dt)
}

function makePointerState() {
  return {
    fx:   new OneEuro(POINTER_MIN_CUTOFF, POINTER_BETA, POINTER_D_CUTOFF),
    fy:   new OneEuro(POINTER_MIN_CUTOFF, POINTER_BETA, POINTER_D_CUTOFF),
    outX: null,
    outY: null,
  }
}

function smoothPointer(state, x, y, t) {
  const nx = state.fx.filter(x, t)
  const ny = state.fy.filter(y, t)
  if (state.outX === null) {
    state.outX = nx; state.outY = ny
    return [nx, ny]
  }
  if (Math.abs(nx - state.outX) < POINTER_DEADZONE &&
      Math.abs(ny - state.outY) < POINTER_DEADZONE) {
    return [state.outX, state.outY]   // 데드존: 시각적 완전 정지
  }
  state.outX = nx; state.outY = ny
  return [nx, ny]
}

function resetPointerState(s) {
  s.fx.reset(); s.fy.reset()
  s.outX = null; s.outY = null
}

// ── 카메라 ───────────────────────────────────────────────────────────────────
async function openCamera() {
  for (let attempt = 1; attempt <= CAM_RETRY_COUNT; attempt++) {
    try {
      return await navigator.mediaDevices.getUserMedia({
        video: {
          width:     { ideal: CAM_W },
          height:    { ideal: CAM_H },
          frameRate: { ideal: 30 },
        },
      })
    } catch (err) {
      const retryable = err.name === 'NotReadableError' || err.name === 'AbortError'
      if (!retryable || attempt === CAM_RETRY_COUNT) throw err
      console.warn(`[useGesture] 카메라 열기 실패 (${attempt}/${CAM_RETRY_COUNT}):`, err.message)
      await new Promise(r => setTimeout(r, CAM_RETRY_DELAY))
    }
  }
}

/**
 * 온디바이스 MediaPipe Hands.
 *
 * @param {Object} opts
 * @param {(pos: {x:number, y:number}|null) => void} opts.onPointer
 *        포인터(정규화 0~1) 콜백. 매 MediaPipe 프레임마다 호출 — 네트워크 대기 없음.
 *        손이 사라지면 null 호출.
 * @param {(data: Object) => void} opts.onGesture
 *        서버 응답 콜백. 제스처/손가락 수 등.
 * @param {boolean} opts.enabled
 */
export function useGesture({ onPointer, onGesture, onLandmarks, videoRef, enabled = true }) {
  const pointerRef   = useRef(onPointer)
  const gestureRef   = useRef(onGesture)
  const landmarksRef = useRef(onLandmarks)
  useEffect(() => { pointerRef.current   = onPointer   }, [onPointer])
  useEffect(() => { gestureRef.current   = onGesture   }, [onGesture])
  useEffect(() => { landmarksRef.current = onLandmarks }, [onLandmarks])

  useEffect(() => {
    if (!enabled) return

    let ws       = null
    let stream   = null
    let video    = null
    let hands    = null
    let rafId    = null
    let active   = true
    let inflight = false
    let lastSent = 0

    const pointerStates = { Left: makePointerState(), Right: makePointerState() }

    const handleResults = (results) => {
      if (!active) return
      inflight = false

      const lms    = results.multiHandLandmarks || []
      const handed = results.multiHandedness     || []

      // 사용자의 오른손(MediaPipe "Left") 우선
      let activeIdx = -1
      let activeLabel = null
      for (let i = 0; i < handed.length; i++) {
        const lbl = handed[i]?.label
        if (lbl === 'Left') { activeIdx = i; activeLabel = 'Left'; break }
        if (lbl === 'Right' && activeIdx < 0) { activeIdx = i; activeLabel = 'Right' }
      }

      // ── 포인터: 즉시 로컬 계산 + 콜백 ─────────────────────────────────
      if (activeIdx >= 0) {
        const lm = lms[activeIdx]
        const px = (lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 4
        const py = (lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 4
        const [sx, sy] = smoothPointer(
          pointerStates[activeLabel], px, py, performance.now() / 1000
        )
        pointerRef.current?.({ x: sx, y: sy })
      } else {
        pointerRef.current?.(null)
      }

      // 현재 안 보이는 손은 필터 reset
      const seen = new Set(handed.map(h => h?.label).filter(Boolean))
      for (const lbl of ['Left', 'Right']) {
        if (!seen.has(lbl)) resetPointerState(pointerStates[lbl])
      }

      // ── 랜드마크 페이로드 생성 ────────────────────────────────────────
      const handsPayload = []
      for (let i = 0; i < lms.length; i++) {
        const lm   = lms[i]
        const flat = new Array(63)
        for (let j = 0; j < 21; j++) {
          flat[j*3]     = lm[j].x
          flat[j*3 + 1] = lm[j].y
          flat[j*3 + 2] = lm[j].z
        }
        handsPayload.push({
          label: handed[i]?.label || 'Right',
          lm:    flat,
        })
      }

      // onLandmarks: 수집 도구용 (매 프레임 원시 랜드마크 전달)
      if (landmarksRef.current) {
        landmarksRef.current(handsPayload)
      }

      // ── 서버로 랜드마크 전송 (제스처 분류용) ─────────────────────────
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ hands: handsPayload }))
      }
    }

    const loop = async () => {
      if (!active) return
      const now = performance.now()
      const ready =
        !inflight &&
        video && video.readyState >= 2 &&
        hands &&
        now - lastSent >= 1000 / MAX_FPS

      if (ready) {
        inflight = true
        lastSent = now
        try {
          await hands.send({ image: video })
        } catch (err) {
          inflight = false
          console.warn('[useGesture] hands.send 오류:', err)
        }
      }
      rafId = requestAnimationFrame(loop)
    }

    const setup = async () => {
      try {
        stream = await openCamera()
        if (!active) { stream.getTracks().forEach(t => t.stop()); return }

        video = document.createElement('video')
        video.srcObject = stream
        video.muted = true
        video.setAttribute('playsinline', '')
        await video.play()
        if (!active) return
        if (videoRef) videoRef.current = video

        hands = new Hands({ locateFile: (f) => `${MP_BASE}${f}` })
        hands.setOptions({
          maxNumHands:            2,
          modelComplexity:        1,
          minDetectionConfidence: 0.6,
          minTrackingConfidence:  0.5,
        })
        hands.onResults(handleResults)

        ws = new WebSocket(WS_URL)
        ws.onopen    = () => { loop() }
        ws.onmessage = (e) => {
          try { gestureRef.current?.(JSON.parse(e.data)) } catch {}
        }
        ws.onerror = () => { console.warn('[useGesture] WebSocket 오류') }
        ws.onclose = () => {}

      } catch (err) {
        if (!active) return
        console.error('[useGesture] 초기화 실패:', err)
      }
    }

    setup()

    return () => {
      active = false
      if (rafId) cancelAnimationFrame(rafId)
      ws?.close()
      try { hands?.close?.() } catch {}
      stream?.getTracks().forEach(t => t.stop())
      if (videoRef) videoRef.current = null
    }
  }, [enabled])
}
