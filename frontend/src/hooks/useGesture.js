import { useEffect, useRef } from 'react'
import { Hands } from '@mediapipe/hands'

// ── 카메라 설정 ──────────────────────────────────────────────────────────────
const CAM_W   = 640
const CAM_H   = 480
const MAX_FPS = 30

const MP_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/'

const CAM_RETRY_COUNT = 4
const CAM_RETRY_DELAY = 1500

// ── 포인터 스무딩 파라미터 ────────────────────────────────────────────────────
const POINTER_MIN_CUTOFF = 0.15
const POINTER_BETA       = 50.0
const POINTER_D_CUTOFF   = 1.0
const POINTER_DEADZONE   = 0.0018
const POINTER_MIRROR_X   = false

// ── 손가락 펴짐 감지 ─────────────────────────────────────────────────────────
const EXTENSION_MARGIN_STRICT = 1.15
const EXTENSION_MARGIN_THUMB  = 1.05
const EXTENSION_MARGIN_LOOSE  = 1.05  // 스와이프 open-hand 판정

function _dist2d(a, b) {
  if (!a || !b) return Number.NaN
  if (!Number.isFinite(a.x) || !Number.isFinite(a.y) ||
      !Number.isFinite(b.x) || !Number.isFinite(b.y)) return Number.NaN
  const dx = a.x - b.x, dy = a.y - b.y
  return Math.sqrt(dx * dx + dy * dy)
}

// z(깊이)까지 포함한 3D 거리 — 카메라 평면에서 겹쳐 보이지만 실제론 떨어진 동작 구분용
function _dist3d(a, b) {
  if (!a || !b) return Number.NaN
  if (!Number.isFinite(a.x) || !Number.isFinite(a.y) ||
      !Number.isFinite(b.x) || !Number.isFinite(b.y)) return Number.NaN
  const dx = a.x - b.x, dy = a.y - b.y
  // z는 없을 수도 있으므로 0으로 fallback
  const dz = (Number.isFinite(a.z) && Number.isFinite(b.z)) ? (a.z - b.z) : 0
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
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

// 커서 활성 A: 검지만 핀 (엄지 무관)
function _isPointing(lm) {
  return (
     _isFingerExtended(lm, 8,  6) &&
    !_isFingerExtended(lm, 12, 10) &&
    !_isFingerExtended(lm, 16, 14) &&
    !_isFingerExtended(lm, 20, 18)
  )
}

// 커서 활성 B: 엄지+검지 동시에 핀 (핀치 전 준비 자세)
function _isThumbIndexOpen(lm) {
  return (
    _isThumbExtended(lm)            &&
     _isFingerExtended(lm, 8,  6)   &&
    !_isFingerExtended(lm, 12, 10)  &&
    !_isFingerExtended(lm, 16, 14)  &&
    !_isFingerExtended(lm, 20, 18)
  )
}

// 핀치: 엄지 끝(4) ↔ 검지 끝(8) 3D 거리 + 검지 부분 펴짐 확인
// - 2D(x,y)만 쓰면 손을 옆으로 돌려 노드만 겹쳐도 핀치로 오인식됨
// - 3D 거리를 쓰면 z(깊이) 차이가 커서 해당 동작이 걸러짐
// - 주먹도 검지 부분 펴짐 조건으로 추가 차단
const PINCH_DIST_THRESHOLD = 0.06
function _isPinching(lm) {
  const d = _dist3d(lm[4], lm[8])
  if (!Number.isFinite(d) || d >= PINCH_DIST_THRESHOLD) return false
  return _isFingerExtended(lm, 8, 6, 0.8)
}

// 앵커 기반 매핑 범위 (±이 범위가 전체 화면에 매핑)
const ANCHOR_WINDOW_HALF = 0.25
// 엣지 도달 시 앵커 이동 비율 (프레임당, 높을수록 빠르게 따라옴 0.0~1.0)
const EDGE_FOLLOW_RATE   = 0.15

// ── 클라이언트 사이드 제스처 인식 ────────────────────────────────────────────

function _countFingers(lm) {
  let n = _isThumbExtended(lm) ? 1 : 0
  for (const [tip, pip] of [[8,6],[12,10],[16,14],[20,18]])
    if (_isFingerExtended(lm, tip, pip)) n++
  return n
}

function _isOpenForSwipe(lm) {
  let n = _isThumbExtended(lm) ? 1 : 0
  for (const [tip, pip] of [[8,6],[12,10],[16,14],[20,18]])
    if (_isFingerExtended(lm, tip, pip, EXTENSION_MARGIN_LOOSE)) n++
  return n >= 3
}

function _classifyStatic(lm) {
  if (_isPinching(lm)) return 'ok'
  const t = _isThumbExtended(lm)
  const i = _isFingerExtended(lm, 8,  6)
  const m = _isFingerExtended(lm, 12, 10)
  const r = _isFingerExtended(lm, 16, 14)
  const p = _isFingerExtended(lm, 20, 18)
  const n = [t, i, m, r, p].filter(Boolean).length
  if (n === 1 && i)                return 'finger_1'
  if (n === 2 && i && m)           return 'finger_2'
  if (n === 3 && i && m && r)      return 'finger_3'
  if (n === 4 && i && m && r && p) return 'finger_4'
  if (n === 5)                     return 'finger_5'
  return null
}

// FSM debounce
const G_CONFIRM     = 3
const G_CONFIRM_OK  = 4
const G_COOLDOWN    = 800
const G_COOLDOWN_OK = 600

function makeGestureState() {
  return { candidate: null, count: 0, lastFire: -Infinity }
}

function _confirmStatic(state, gesture) {
  const now = performance.now()
  const cooldown = gesture === 'ok' ? G_COOLDOWN_OK : G_COOLDOWN
  if (now - state.lastFire < cooldown) return null
  if (gesture !== null && gesture === state.candidate) {
    state.count++
  } else {
    state.candidate = gesture
    state.count     = gesture ? 1 : 0
  }
  const needed = gesture === 'ok' ? G_CONFIRM_OK : G_CONFIRM
  if (state.count >= needed && gesture !== null) {
    state.count    = 0
    state.lastFire = now
    return gesture
  }
  return null
}

// 스와이프 파라미터
const SWIPE_COOLDOWN_MS      = 600   // 같은 방향 / 무관 쿨다운
const SWIPE_COOLDOWN_REVERSE = 1500  // 직전과 반대 방향 쿨다운 (복귀 동작 오인식 방지)
const SWIPE_WINDOW_MS        = 600
const SWIPE_MIN_FRAMES   = 5

// 좌우 — x 변위 최소치 / y 최대 허용 오차
const SWIPE_LR_MIN_X     = 0.12
const SWIPE_LR_MAX_Y     = 0.07
// 상하 — y 변위 최소치 / x 최대 허용 오차
const SWIPE_UD_MIN_Y     = 0.10
const SWIPE_UD_MAX_X     = 0.07
// 직선도: 순변위 / 총경로 길이 (1=완전직선, 낮을수록 꺾임)
const SWIPE_STRAIGHTNESS = 0.55
// 방향 일관성: 같은 방향 스텝 비율 (흔들림/왕복 제거)
const SWIPE_CONSISTENCY  = 0.65

const _SWIPE_REVERSE = {
  swipe_left: 'swipe_right', swipe_right: 'swipe_left',
  swipe_up:   'swipe_down',  swipe_down:  'swipe_up',
}

// X는 화면 미러링 반영: 카메라 dx<0 = 사용자 기준 오른쪽 → swipe_right
function _detectSwipe(buf, lastSwipeT, lastSwipeDir, lm) {
  if (!_isOpenForSwipe(lm)) return null
  if (buf.length < SWIPE_MIN_FRAMES) return null

  const dx = buf[buf.length - 1].x - buf[0].x
  const dy = buf[buf.length - 1].y - buf[0].y
  const adx = Math.abs(dx), ady = Math.abs(dy)
  const netDist = Math.sqrt(dx * dx + dy * dy)
  if (netDist < 0.04) return null

  // ① 방향 후보 판별
  let candidate = null
  if (adx >= ady && adx >= SWIPE_LR_MIN_X && ady <= SWIPE_LR_MAX_Y) {
    let pos = 0, neg = 0
    for (let i = 1; i < buf.length; i++) {
      const step = buf[i].x - buf[i-1].x
      if (step >  0.001) pos++
      else if (step < -0.001) neg++
    }
    const total = pos + neg
    if (total === 0 || Math.max(pos, neg) / total < SWIPE_CONSISTENCY) return null
    candidate = dx < 0 ? 'swipe_right' : 'swipe_left'
  } else if (ady > adx && ady >= SWIPE_UD_MIN_Y && adx <= SWIPE_UD_MAX_X) {
    candidate = dy < 0 ? 'swipe_up' : 'swipe_down'
  }
  if (!candidate) return null

  // ② 방향별 쿨다운: 직전과 반대 방향은 더 길게 (복귀 동작 오인식 방지)
  const isReverse = lastSwipeDir && _SWIPE_REVERSE[lastSwipeDir] === candidate
  const cooldown  = isReverse ? SWIPE_COOLDOWN_REVERSE : SWIPE_COOLDOWN_MS
  if (performance.now() - lastSwipeT < cooldown) return null

  // ③ 직선도 체크
  let pathLen = 0
  for (let i = 1; i < buf.length; i++) {
    const px = buf[i].x - buf[i-1].x, py = buf[i].y - buf[i-1].y
    pathLen += Math.sqrt(px * px + py * py)
  }
  if (netDist / (pathLen + 1e-6) < SWIPE_STRAIGHTNESS) return null

  return candidate
}

const _GESTURE_PRIORITY = {
  ok: 3,
  swipe_left: 2, swipe_right: 2, swipe_up: 2, swipe_down: 2,
  finger_1: 1, finger_2: 1, finger_3: 1, finger_4: 1, finger_5: 1,
}

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
  reset() { this.xPrev = null; this.dxPrev = 0; this.tPrev = null }
  filter(x, t) {
    if (this.xPrev === null) { this.xPrev = x; this.tPrev = t; return x }
    const dt     = Math.max(t - this.tPrev, 1e-6)
    const dx     = (x - this.xPrev) / dt
    const aD     = lpfAlpha(this.dCutoff, dt)
    const dxHat  = aD * dx + (1 - aD) * this.dxPrev
    const cutoff = this.minCutoff + this.beta * Math.abs(dxHat)
    const a      = lpfAlpha(cutoff, dt)
    const xHat   = a * x + (1 - a) * this.xPrev
    this.xPrev   = xHat
    this.dxPrev  = dxHat
    this.tPrev   = t
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
  if (state.outX === null) { state.outX = nx; state.outY = ny; return [nx, ny] }
  if (Math.abs(nx - state.outX) < POINTER_DEADZONE &&
      Math.abs(ny - state.outY) < POINTER_DEADZONE) {
    return [state.outX, state.outY]
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
        video: { width: { ideal: CAM_W }, height: { ideal: CAM_H }, frameRate: { ideal: 30 } },
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
 * 온디바이스 MediaPipe Hands — 모든 제스처 인식을 클라이언트에서 처리.
 *
 * @param {(pos: {x,y}|null) => void} opts.onPointer  정규화 커서 위치 (매 프레임)
 * @param {(data: Object)    => void} opts.onGesture  제스처 결과 (매 프레임)
 * @param {(payload: Array)  => void} opts.onLandmarks 원시 랜드마크 (수집 도구용)
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

    let stream   = null
    let video    = null
    let hands    = null
    let rafId    = null
    let active   = true
    let inflight = false
    let lastSent = 0

    // ── 포인터 상태 ──────────────────────────────────────────────────────────
    const pointerStates = { Left: makePointerState(), Right: makePointerState() }
    const anchors       = { Left: null, Right: null }
    const wasActive     = { Left: false, Right: false }
    const CURSOR_HIDE_DELAY_MS = 350
    const hideTimers    = { Left: null, Right: null }

    // ── 제스처 상태 ──────────────────────────────────────────────────────────
    const gestureStates = { Left: makeGestureState(), Right: makeGestureState() }
    const palmBufs      = { Left: [], Right: [] }
    const lastSwipes    = { Left: -Infinity, Right: -Infinity }
    const lastSwipeDirs = { Left: null, Right: null }

    const handleResults = (results) => {
      if (!active) return
      clearTimeout(inflightWatchdog)
      inflight = false

      const lms    = results.multiHandLandmarks || []
      const handed = results.multiHandedness     || []

      // 사용자의 오른손(MediaPipe "Left") 우선
      let activeIdx   = -1
      let activeLabel = null
      for (let i = 0; i < handed.length; i++) {
        const lbl = handed[i]?.label
        if (lbl === 'Left')  { activeIdx = i; activeLabel = 'Left';  break }
        if (lbl === 'Right' && activeIdx < 0) { activeIdx = i; activeLabel = 'Right' }
      }

      // ── 포인터 ────────────────────────────────────────────────────────────
      try {
        if (activeIdx >= 0 && _isValidLandmarks(lms[activeIdx])) {
          const lm       = lms[activeIdx]
          const pointing = _isPointing(lm) || _isThumbIndexOpen(lm)
          const pinching = !pointing && _isPinching(lm)

          if (pointing || pinching) {
            clearTimeout(hideTimers[activeLabel])
            hideTimers[activeLabel] = null

            const px = (lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 4
            const py = (lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 4

            if (Number.isFinite(px) && Number.isFinite(py)) {
              if (!wasActive[activeLabel]) anchors[activeLabel] = { x: px, y: py }
              wasActive[activeLabel] = true

              const anchor   = anchors[activeLabel]
              const relX     = (px - anchor.x) / ANCHOR_WINDOW_HALF
              const relY     = (py - anchor.y) / ANCHOR_WINDOW_HALF
              const baseX    = POINTER_MIRROR_X ? (1 - anchor.x) : anchor.x
              const dirX     = POINTER_MIRROR_X ? -1 : 1
              const rawNormX = baseX + relX * 0.5 * dirX
              const rawNormY = anchor.y + relY * 0.5
              // 커서가 화면 끝을 벗어나면 앵커를 손 방향으로 조금씩 이동
              // → 클러칭 없이 화면 끝 너머로 계속 이동 가능
              if (rawNormX > 1 || rawNormX < 0)
                anchor.x += (px - anchor.x) * EDGE_FOLLOW_RATE
              if (rawNormY > 1 || rawNormY < 0)
                anchor.y += (py - anchor.y) * EDGE_FOLLOW_RATE
              const normX  = Math.max(0, Math.min(1, rawNormX))
              const normY  = Math.max(0, Math.min(1, rawNormY))
              const [sx, sy] = smoothPointer(
                pointerStates[activeLabel], normX, normY, performance.now() / 1000
              )
              pointerRef.current?.({ x: sx, y: sy })
            } else {
              clearTimeout(hideTimers[activeLabel])
              hideTimers[activeLabel] = null
              wasActive[activeLabel]  = false
              anchors[activeLabel]    = null
              pointerRef.current?.(null)
            }
          } else {
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
          if (activeLabel) { clearTimeout(hideTimers[activeLabel]); hideTimers[activeLabel] = null }
          pointerRef.current?.(null)
        }
      } catch (e) {
        console.warn('[useGesture] 포인터 계산 오류:', e)
        pointerRef.current?.(null)
      }

      // 안 보이는 손 리셋
      const seen = new Set(handed.map(h => h?.label).filter(Boolean))
      for (const lbl of ['Left', 'Right']) {
        if (!seen.has(lbl)) {
          clearTimeout(hideTimers[lbl])
          hideTimers[lbl]       = null
          resetPointerState(pointerStates[lbl])
          anchors[lbl]          = null
          wasActive[lbl]        = false
          gestureStates[lbl]    = makeGestureState()
          palmBufs[lbl].length  = 0
          lastSwipeDirs[lbl]    = null
        }
      }

      // ── 랜드마크 페이로드 (수집 도구용) ───────────────────────────────────
      const handsPayload = []
      for (let i = 0; i < lms.length; i++) {
        const lm = lms[i]
        if (!_isValidLandmarks(lm)) continue
        const flat = new Array(63)
        for (let j = 0; j < 21; j++) {
          flat[j*3] = lm[j].x; flat[j*3+1] = lm[j].y; flat[j*3+2] = lm[j].z
        }
        handsPayload.push({ label: handed[i]?.label || 'Right', lm: flat })
      }
      landmarksRef.current?.(handsPayload)

      // ── 제스처 인식 (클라이언트 전담) ────────────────────────────────────
      const handData = {}
      const frameNow = performance.now()

      for (let i = 0; i < lms.length; i++) {
        const lm = lms[i]
        if (!_isValidLandmarks(lm)) continue
        const mpLabel = handed[i]?.label || 'Right'
        const side    = mpLabel === 'Left' ? 'right' : 'left'

        // 원시 손바닥 중심 — 앵커 변환 없이 절대 위치 (스와이프 추적용)
        const rpx = (lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 4
        const rpy = (lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 4
        palmBufs[mpLabel].push({ x: rpx, y: rpy, t: frameNow })
        const cutoff = frameNow - SWIPE_WINDOW_MS
        while (palmBufs[mpLabel].length && palmBufs[mpLabel][0].t < cutoff)
          palmBufs[mpLabel].shift()

        let gesture = null
        const swipe = _detectSwipe(palmBufs[mpLabel], lastSwipes[mpLabel], lastSwipeDirs[mpLabel], lm)
        if (swipe) {
          lastSwipes[mpLabel]              = frameNow
          lastSwipeDirs[mpLabel]           = swipe
          palmBufs[mpLabel].length         = 0
          gestureStates[mpLabel].candidate = null
          gestureStates[mpLabel].count     = 0
          gesture = swipe
        } else {
          gesture = _confirmStatic(gestureStates[mpLabel], _classifyStatic(lm))
        }

        handData[side] = {
          gesture,
          finger_count:   _countFingers(lm),
          pinch_distance: +_dist3d(lm[4], lm[8]).toFixed(4),
          is_pointing:    _isPointing(lm) || _isThumbIndexOpen(lm),
        }
      }

      const fired    = Object.values(handData).map(d => d.gesture).filter(Boolean)
      const dominant = fired.length
        ? fired.reduce((a, b) =>
            (_GESTURE_PRIORITY[a] ?? 0) >= (_GESTURE_PRIORITY[b] ?? 0) ? a : b)
        : null

      gestureRef.current?.({
        hands:         { left: handData.left ?? null, right: handData.right ?? null },
        total_fingers: Object.values(handData).reduce((s, d) => s + d.finger_count, 0),
        gesture:       dominant,
      })
    }

    // inflight 워치독
    let inflightWatchdog = null

    const loop = () => {
      if (!active) return
      const now   = performance.now()
      const ready = !inflight && video && video.readyState >= 2 && hands &&
                    now - lastSent >= 1000 / MAX_FPS
      if (ready) {
        inflight = true
        lastSent = now
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
        loop()

      } catch (err) {
        if (!active) return
        console.error('[useGesture] 초기화 실패:', err)
      }
    }

    setup()

    return () => {
      active = false
      clearTimeout(inflightWatchdog)
      clearTimeout(hideTimers.Left)
      clearTimeout(hideTimers.Right)
      if (rafId) cancelAnimationFrame(rafId)
      try { hands?.close?.() } catch {}
      stream?.getTracks().forEach(t => t.stop())
      if (videoRef) videoRef.current = null
    }
  }, [enabled])
}
