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
const POINTER_MIRROR_X   = false  // 좌우 반전 적용 여부

// ── 손가락 펴짐 감지 (백엔드와 동일 마진) ───────────────────────────────────
const EXTENSION_MARGIN_STRICT = 1.15
const EXTENSION_MARGIN_THUMB  = 1.05

function _dist2d(a, b) {
  if (!a || !b) return Number.NaN
  if (!Number.isFinite(a.x) || !Number.isFinite(a.y) ||
      !Number.isFinite(b.x) || !Number.isFinite(b.y)) {
    return Number.NaN
  }
  const dx = a.x - b.x, dy = a.y - b.y
  return Math.sqrt(dx * dx + dy * dy)
}

function _isValidLandmarks(lm) {
  if (!lm || lm.length < 21) return false
  for (let i = 0; i < 21; i++) {
    const p = lm[i]
    if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)) return false
  }
  return true
}

function _isFingerExtended(lm, tipIdx, pipIdx, margin = EXTENSION_MARGIN_STRICT) {
  const wrist = lm[0]
  const dTip = _dist2d(lm[tipIdx], wrist)
  const dPip = _dist2d(lm[pipIdx], wrist)
  if (!Number.isFinite(dTip) || !Number.isFinite(dPip)) return false
  return dTip > dPip * margin
}

function _isThumbExtended(lm) {
  const dTip = _dist2d(lm[4], lm[5])
  const dPip = _dist2d(lm[3], lm[5])
  if (!Number.isFinite(dTip) || !Number.isFinite(dPip)) return false
  return dTip > dPip * EXTENSION_MARGIN_THUMB
}

// 커서 활성 조건 A: 검지만 핀 (엄지 무관)
function _isPointing(lm) {
  return (
    _isFingerExtended(lm, 8,  6)  &&
    !_isFingerExtended(lm, 12, 10) &&
    !_isFingerExtended(lm, 16, 14) &&
    !_isFingerExtended(lm, 20, 18)
  )
}

// 커서 활성 조건 B: 엄지+검지 동시에 핀 (핀치 전 준비 자세)
// _isPointing이 이미 엄지를 무시하지만, 엄지 펴짐 시 손 geometry 변화로
// 검지 판정이 흔들리는 경우를 명시적으로 보완
function _isThumbIndexOpen(lm) {
  return (
    _isThumbExtended(lm)            &&
    _isFingerExtended(lm, 8,  6)   &&
    !_isFingerExtended(lm, 12, 10) &&
    !_isFingerExtended(lm, 16, 14) &&
    !_isFingerExtended(lm, 20, 18)
  )
}

// 엄지 끝(4) ↔ 검지 끝(8) 거리가 임계값 이하 → 핀치(확인 동작)
const PINCH_DIST_THRESHOLD = 0.08
function _isPinching(lm) {
  const d = _dist2d(lm[4], lm[8])
  return Number.isFinite(d) && d < PINCH_DIST_THRESHOLD
}

// 앵커 기반 매핑: 검지를 핀 시점을 중심으로 이 범위(±) 안의 손 움직임을 전체 화면에 매핑
// 값을 낮출수록 조금만 움직여도 커서가 끝까지 이동
const ANCHOR_WINDOW_HALF = 0.25

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
    const anchors       = { Left: null, Right: null }
    const wasActive     = { Left: false, Right: false }
    // 커서 숨김 지연 — 포인팅→핀치 전환 순간의 찰나 gap에 커서가 꺼지지 않도록
    const CURSOR_HIDE_DELAY_MS = 350
    const hideTimers    = { Left: null, Right: null }

    const handleResults = (results) => {
      if (!active) return
      clearTimeout(inflightWatchdog)
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

      // ── 포인터: 앵커 기반 로컬 매핑 ────────────────────────────────────
      // 포인터 계산은 독립 블록 — 여기서 실패해도 아래 WS 전송은 반드시 실행됨
      try {
        if (activeIdx >= 0 && _isValidLandmarks(lms[activeIdx])) {
          const lm       = lms[activeIdx]
          const pointing = _isPointing(lm) || _isThumbIndexOpen(lm)
          const pinching = !pointing && _isPinching(lm)

          if (pointing || pinching) {
            // 활성 상태 → 지연 타이머 취소
            clearTimeout(hideTimers[activeLabel])
            hideTimers[activeLabel] = null

            const px = (lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 4
            const py = (lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 4

            if (Number.isFinite(px) && Number.isFinite(py)) {
              if (pointing) {
                if (!wasActive[activeLabel]) {
                  anchors[activeLabel] = { x: px, y: py }
                }
                wasActive[activeLabel] = true

                const anchor = anchors[activeLabel]
                const relX   = (px - anchor.x) / ANCHOR_WINDOW_HALF
                const relY   = (py - anchor.y) / ANCHOR_WINDOW_HALF
                const baseX  = POINTER_MIRROR_X ? (1 - anchor.x) : anchor.x
                const dirX   = POINTER_MIRROR_X ? -1 : 1
                const normX  = Math.max(0, Math.min(1, baseX + relX * 0.5 * dirX))
                const normY  = Math.max(0, Math.min(1, anchor.y + relY * 0.5))
                const [sx, sy] = smoothPointer(
                  pointerStates[activeLabel], normX, normY, performance.now() / 1000
                )
                pointerRef.current?.({ x: sx, y: sy })
              } else {
                // 핀치(확인 동작): 포인팅과 동일하게 커서 이동
                if (!wasActive[activeLabel]) {
                  anchors[activeLabel] = { x: px, y: py }
                }
                wasActive[activeLabel] = true

                const anchor = anchors[activeLabel]
                const relX   = (px - anchor.x) / ANCHOR_WINDOW_HALF
                const relY   = (py - anchor.y) / ANCHOR_WINDOW_HALF
                const baseX  = POINTER_MIRROR_X ? (1 - anchor.x) : anchor.x
                const dirX   = POINTER_MIRROR_X ? -1 : 1
                const normX  = Math.max(0, Math.min(1, baseX + relX * 0.5 * dirX))
                const normY  = Math.max(0, Math.min(1, anchor.y + relY * 0.5))
                const [sx, sy] = smoothPointer(
                  pointerStates[activeLabel], normX, normY, performance.now() / 1000
                )
                pointerRef.current?.({ x: sx, y: sy })
              }
            } else {
              // 좌표 이상 — 즉시 숨김
              clearTimeout(hideTimers[activeLabel])
              hideTimers[activeLabel] = null
              wasActive[activeLabel]  = false
              anchors[activeLabel]    = null
              pointerRef.current?.(null)
            }
          } else {
            // 비활성 — CURSOR_HIDE_DELAY_MS 후에 커서 숨김 (전환 gap 보호)
            if (!hideTimers[activeLabel]) {
              hideTimers[activeLabel] = setTimeout(() => {
                hideTimers[activeLabel] = null
                wasActive[activeLabel]  = false
                anchors[activeLabel]    = null
                pointerRef.current?.(null)
              }, CURSOR_HIDE_DELAY_MS)
            }
          }
        } else {
          // 손이 사라짐 — 지연 없이 즉시 숨김
          if (activeLabel) {
            clearTimeout(hideTimers[activeLabel])
            hideTimers[activeLabel] = null
          }
          pointerRef.current?.(null)
        }
      } catch (e) {
        console.warn('[useGesture] 포인터 계산 오류:', e)
        pointerRef.current?.(null)
      }

      // 현재 안 보이는 손은 필터·앵커·타이머 reset
      const seen = new Set(handed.map(h => h?.label).filter(Boolean))
      for (const lbl of ['Left', 'Right']) {
        if (!seen.has(lbl)) {
          clearTimeout(hideTimers[lbl])
          hideTimers[lbl] = null
          resetPointerState(pointerStates[lbl])
          anchors[lbl]   = null
          wasActive[lbl] = false
        }
      }

      // ── 랜드마크 페이로드 생성 ────────────────────────────────────────
      const handsPayload = []
      for (let i = 0; i < lms.length; i++) {
        const lm = lms[i]
        if (!_isValidLandmarks(lm)) continue

        const flat = new Array(63)
        for (let j = 0; j < 21; j++) {
          const p = lm[j]
          flat[j*3]     = p.x
          flat[j*3 + 1] = p.y
          flat[j*3 + 2] = p.z
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

    // inflight 워치독: hands.send()가 영구 hang하면 3초 후 강제 해제
    let inflightWatchdog = null

    const loop = () => {          // async 제거 — RAF가 항상 예약되도록
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
        // 워치독: onResults가 3초 내에 호출 안 되면 inflight 강제 해제
        inflightWatchdog = setTimeout(() => {
          console.warn('[useGesture] hands.send 타임아웃 — inflight 강제 해제')
          inflight = false
        }, 3000)
        hands.send({ image: video }).catch(err => {
          clearTimeout(inflightWatchdog)
          inflight = false
          console.warn('[useGesture] hands.send 오류:', err)
        })
      }
      // await 없이 항상 다음 RAF 예약 — hands.send hang에도 루프 생존
      rafId = requestAnimationFrame(loop)
    }

    // WebSocket — 인식 루프와 독립적으로 관리, 끊기면 재연결
    let wsReconnectTimer = null
    const openWs = () => {
      if (!active) return
      ws = new WebSocket(WS_URL)
      ws.onmessage = (e) => {
        try { gestureRef.current?.(JSON.parse(e.data)) } catch {}
      }
      ws.onerror = () => { console.warn('[useGesture] WebSocket 오류') }
      ws.onclose = () => {
        if (active) wsReconnectTimer = setTimeout(openWs, 2000)
      }
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

        // 루프는 WS와 독립적으로 즉시 시작
        loop()
        openWs()

      } catch (err) {
        if (!active) return
        console.error('[useGesture] 초기화 실패:', err)
      }
    }

    setup()

    return () => {
      active = false
      clearTimeout(inflightWatchdog)
      clearTimeout(wsReconnectTimer)
      clearTimeout(hideTimers.Left)
      clearTimeout(hideTimers.Right)
      if (rafId) cancelAnimationFrame(rafId)
      ws?.close()
      try { hands?.close?.() } catch {}
      stream?.getTracks().forEach(t => t.stop())
      if (videoRef) videoRef.current = null
    }
  }, [enabled])
}
