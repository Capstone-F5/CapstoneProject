import { useEffect, useRef } from 'react'
import { Hands } from '@mediapipe/hands'

// ── 카메라 설정 ──────────────────────────────────────────────────────────────
const CAM_W   = 640
const CAM_H   = 480
const MAX_FPS = 20
const AR_REF  = CAM_W / CAM_H

const MP_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/'

const CAM_RETRY_COUNT = 4
const CAM_RETRY_DELAY = 1500

// ── 포인터 스무딩 파라미터 (1 유로 필터) ──────────────────────────────────────────
const POINTER_MIN_CUTOFF = 0.15
const POINTER_BETA       = 50.0
const POINTER_D_CUTOFF   = 1.0
const POINTER_DEADZONE   = 0.0018
const POINTER_MIRROR_X   = false

// ── 손가락 펴짐 감지 파라미터 ──────────────────────────────────────────────────
const EXTENSION_MARGIN_STRICT = 1.15
const EXTENSION_MARGIN_THUMB  = 1.05
const EXTENSION_MARGIN_LOOSE  = 1.05  
const EXTENSION_MARGIN_POINT       = 1.08
const EXTENSION_MARGIN_POINT_HOLD  = 1.00
const EXTENSION_MARGIN_FOLD_HOLD   = 1.18  

function _dist2d(a, b) {
  if (!a || !b) return Number.NaN
  if (!Number.isFinite(a.x) || !Number.isFinite(a.y) ||
      !Number.isFinite(b.x) || !Number.isFinite(b.y)) return Number.NaN
  const dx = a.x - b.x, dy = a.y - b.y
  return Math.sqrt(dx * dx + dy * dy)
}

function _dist3d(a, b) {
  if (!a || !b) return Number.NaN
  const dx = a.x - b.x, dy = a.y - b.y
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

const MIN_PALM_SIZE = 0.10  

function _palmSize(lm) {
  return _dist2d(lm[0], lm[9])
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

function _isPointing(lm) {
  return (
     _isFingerExtended(lm, 8,  6, EXTENSION_MARGIN_POINT) &&
    !_isFingerExtended(lm, 12, 10) &&
    !_isFingerExtended(lm, 16, 14) &&
    !_isFingerExtended(lm, 20, 18)
  )
}

function _isThumbIndexOpen(lm) {
  return (
    _isThumbExtended(lm)                                  &&
     _isFingerExtended(lm, 8,  6, EXTENSION_MARGIN_POINT) &&
    !_isFingerExtended(lm, 12, 10)                        &&
    !_isFingerExtended(lm, 16, 14)                        &&
    !_isFingerExtended(lm, 20, 18)
  )
}

function _isPointingHold(lm) {
  const indexOK = _isFingerExtended(lm, 8, 6, EXTENSION_MARGIN_POINT_HOLD)
  const otherFolded =
    !_isFingerExtended(lm, 12, 10, EXTENSION_MARGIN_FOLD_HOLD) &&
    !_isFingerExtended(lm, 16, 14, EXTENSION_MARGIN_FOLD_HOLD) &&
    !_isFingerExtended(lm, 20, 18, EXTENSION_MARGIN_FOLD_HOLD)
  return indexOK && otherFolded
}

// 오케이 인식 깐깐하게 조절
const PINCH_RATIO_ENTER = 0.18   
const PINCH_RATIO_EXIT  = 0.30   

function _isPinching(lm, alreadyPinching = false) {
  const palm = _palmSize(lm)
  if (!Number.isFinite(palm) || palm < 1e-6) return false
  const d     = _dist2d(lm[4], lm[8])
  if (!Number.isFinite(d)) return false
  const ratio = d / palm
  const thr   = alreadyPinching ? PINCH_RATIO_EXIT : PINCH_RATIO_ENTER
  if (ratio >= thr) return false
  return _isFingerExtended(lm, 8, 6, 0.8)
}

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

function _classifyStaticNoPinch(lm) {
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

function _classifyStatic(lm) {
  if (_isPinching(lm)) return 'ok'
  return _classifyStaticNoPinch(lm)
}

// 오케이 프레임 확정 수치
const G_CONFIRM     = 3
const G_CONFIRM_OK  = 10      
const G_COOLDOWN    = 800
const G_COOLDOWN_OK = 800     

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

const SWIPE_COOLDOWN_MS      = 600
const SWIPE_COOLDOWN_REVERSE = 1500
const SWIPE_WINDOW_MS        = 700
const SWIPE_MIN_FRAMES       = 4
const SWIPE_STEP_THRESHOLD   = 0.004

// 스와이프 방향을 칼같이 구분하기 위한 엄격한 기준값 적용
const SWIPE_LR_MIN_X     = 0.15  // 기존 0.10 -> 0.15 (가로로 더 길게 그어야 인정)
const SWIPE_LR_MAX_Y     = 0.05  // 기존 0.08 -> 0.05 (가로로 그을 때 위아래 흔들림 얄짤없이 차단)

// 세로(위아래) 스와이프 기준을 사람 관절에 맞게 완화
const SWIPE_UD_MIN_Y     = 0.10  // 0.15 -> 0.10 (너무 길게 안 내려도 인식됨)
const SWIPE_UD_MAX_X     = 0.10  // 0.05 -> 0.10 (손 내릴 때 좌우로 살짝 휘청거리는 궤적 허용)

const SWIPE_STRAIGHTNESS = 0.65  // 0.80 -> 0.65 완벽한 일직선이 아니어도 허용

const SWIPE_CONSISTENCY  = 0.65
const SWIPE_MIN_SPEED    = 0.25

const _SWIPE_REVERSE = {
  swipe_left: 'swipe_right', swipe_right: 'swipe_left',
  swipe_up:   'swipe_down',  swipe_down:  'swipe_up',
}

function _trimBuf(buf) {
  let start = 0
  while (start < buf.length - 2) {
    const d = Math.hypot(buf[start+1].x - buf[start].x, buf[start+1].y - buf[start].y)
    if (d >= SWIPE_STEP_THRESHOLD) break
    start++
  }
  let end = buf.length - 1
  while (end > start + 2) {
    const d = Math.hypot(buf[end].x - buf[end-1].x, buf[end].y - buf[end-1].y)
    if (d >= SWIPE_STEP_THRESHOLD) break
    end--
  }
  return start === 0 && end === buf.length - 1 ? buf : buf.slice(start, end + 1)
}

function _detectSwipe(buf, lastSwipeT, lastSwipeDir, lm, camAR) {
  if (!_isOpenForSwipe(lm)) return null
  const a = _trimBuf(buf)
  if (a.length < SWIPE_MIN_FRAMES) return null
  const xPhys = camAR / AR_REF
  const rawDx = a[a.length - 1].x - a[0].x
  const rawDy = a[a.length - 1].y - a[0].y
  const dx  = rawDx * xPhys
  const dy  = rawDy
  const adx = Math.abs(dx), ady = Math.abs(dy)
  const netDist = Math.sqrt(dx * dx + dy * dy)

  let candidate = null
  if (adx >= ady && adx >= SWIPE_LR_MIN_X && ady <= SWIPE_LR_MAX_Y) {
    let pos = 0, neg = 0
    for (let i = 1; i < a.length; i++) {
      const step = a[i].x - a[i-1].x
      if (step >  0.001) pos++
      else if (step < -0.001) neg++
    }
    const total = pos + neg
    if (total === 0 || Math.max(pos, neg) / total < SWIPE_CONSISTENCY) return null
    candidate = rawDx < 0 ? 'swipe_right' : 'swipe_left'
  } else if (ady > adx && ady >= SWIPE_UD_MIN_Y && adx <= SWIPE_UD_MAX_X) {
    candidate = rawDy < 0 ? 'swipe_up' : 'swipe_down'
  }
  if (!candidate) return null

  const isReverse = lastSwipeDir && _SWIPE_REVERSE[lastSwipeDir] === candidate
  const cooldown  = isReverse ? SWIPE_COOLDOWN_REVERSE : SWIPE_COOLDOWN_MS
  if (performance.now() - lastSwipeT < cooldown) return null

  const dt = (a[a.length - 1].t - a[0].t) / 1000
  if (dt < 0.05 || netDist / dt < SWIPE_MIN_SPEED) return null

  let pathLen = 0
  for (let i = 1; i < a.length; i++) {
    const px = (a[i].x - a[i-1].x) * xPhys
    const py =  a[i].y - a[i-1].y
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
    outX: null, outY: null,
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

const HAND_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [5,9],[9,10],[10,11],[11,12],
  [9,13],[13,14],[14,15],[15,16],
  [13,17],[17,18],[18,19],[19,20],
  [0,17],[5,9],[9,13],[13,17],
]

function _drawPip(canvas, video, lms, handed) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const vw = video.videoWidth, vh = video.videoHeight
  if (!vw || !vh) return
  if (canvas.width !== vw || canvas.height !== vh) {
    canvas.width  = vw
    canvas.height = vh
  }
  ctx.save()
  ctx.translate(vw, 0)
  ctx.scale(-1, 1)
  ctx.drawImage(video, 0, 0)
  ctx.restore()

  for (let hi = 0; hi < lms.length; hi++) {
    const lm    = lms[hi]
    if (!lm || lm.length < 21) continue
    const isRight = handed[hi]?.label === 'Right'
    ctx.lineWidth   = 2.5
    ctx.strokeStyle = isRight ? 'rgba(100,160,255,0.9)' : 'rgba(80,220,130,0.9)'
    for (const [a, b] of HAND_CONNECTIONS) {
      ctx.beginPath()
      ctx.moveTo((1 - lm[a].x) * vw, lm[a].y * vh)
      ctx.lineTo((1 - lm[b].x) * vw, lm[b].y * vh)
      ctx.stroke()
    }
    for (let j = 0; j < 21; j++) {
      const x = (1 - lm[j].x) * vw
      const y = lm[j].y * vh
      const isTip = [4, 8, 12, 16, 20].includes(j)
      ctx.beginPath()
      ctx.arc(x, y, isTip ? 5 : 3, 0, Math.PI * 2)
      ctx.fillStyle   = j === 0 ? 'rgba(255,80,80,0.95)'
                      : isTip  ? 'rgba(255,230,60,0.95)'
                                : 'rgba(255,255,255,0.85)'
      ctx.strokeStyle = 'rgba(0,0,0,0.4)'
      ctx.lineWidth   = 1
      ctx.fill()
      ctx.stroke()
    }
  }
}

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

export function useGesture({ onPointer, onGesture, onLandmarks, videoRef, pipCanvasRef, enabled = true }) {
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
    let camAR    = AR_REF

    // ── 상태 관리 ──────────────────────────────────────────────────────────
    const pointerStates = { Left: makePointerState(), Right: makePointerState() }
    const wasActive     = { Left: false, Right: false }
    const wasPointing   = { Left: false, Right: false }
    const CURSOR_HIDE_DELAY_MS = 350
    const hideTimers    = { Left: null, Right: null }

    const gestureStates = { Left: makeGestureState(), Right: makeGestureState() }
    const palmBufs      = { Left: [], Right: [] }
    const lastSwipes    = { Left: -Infinity, Right: -Infinity }
    const lastSwipeDirs = { Left: null, Right: null }
    const okNeedsOpen   = { Left: false, Right: false }
    const wasPinching   = { Left: false, Right: false }

    const stableFingers = { Left: { count: 0, frames: 0 }, Right: { count: 0, frames: 0 } }
    const STABLE_FRAMES_REQ = 8 // 약 0.3초간 동일한 손가락 개수가 유지되어야 수량 입력으로 확정

    const pinchScroll   = { Left: { anchorX: null, active: false }, Right: { anchorX: null, active: false } }

    const handleResults = (results) => {
      if (!active) return
      clearTimeout(inflightWatchdog)
      inflight = false

      const lms    = results.multiHandLandmarks || []
      const handed = results.multiHandedness     || []

      let activeIdx   = -1
      let activeLabel = null
      for (let i = 0; i < handed.length; i++) {
        const lbl = handed[i]?.label
        if (lbl === 'Left')  { activeIdx = i; activeLabel = 'Left';  break }
        if (lbl === 'Right' && activeIdx < 0) { activeIdx = i; activeLabel = 'Right' }
      }

      // ── 포인터 (인체공학적 사다리꼴 좌표계 적용) ──────────────────────────────────────
      try {
        if (activeIdx >= 0 && _isValidLandmarks(lms[activeIdx]) &&
            _palmSize(lms[activeIdx]) >= MIN_PALM_SIZE) {
          const lm       = lms[activeIdx]
          const pointing = wasPointing[activeLabel]
            ? (_isPointingHold(lm) || _isPointing(lm) || _isThumbIndexOpen(lm))
            : (_isPointing(lm)     || _isThumbIndexOpen(lm))
          const pinching = !pointing && _isPinching(lm, wasPinching[activeLabel])
          wasPointing[activeLabel] = pointing

          const handScore = handed[activeIdx]?.score ?? 1
          if (handScore < 0.7) {
            if (!hideTimers[activeLabel]) {
              hideTimers[activeLabel] = setTimeout(() => {
                hideTimers[activeLabel] = null; wasActive[activeLabel] = false; pointerRef.current?.(null)
              }, CURSOR_HIDE_DELAY_MS)
            }
          } else if (pointing || pinching) {
            clearTimeout(hideTimers[activeLabel])
            hideTimers[activeLabel] = null

            const px = (lm[0].x + lm[9].x) / 2
            const py = (lm[0].y + lm[9].y) / 2

            if (Number.isFinite(px) && Number.isFinite(py)) {
              if (!wasActive[activeLabel]) {
                resetPointerState(pointerStates[activeLabel])
              }
              wasActive[activeLabel] = true

              const pState = pointerStates[activeLabel]
              
              const CAM_LEFT_X  = 0.30; 
              const CAM_RIGHT_X = 0.70; 

              let normX = (px - CAM_LEFT_X) / (CAM_RIGHT_X - CAM_LEFT_X);
              normX = Math.max(0, Math.min(1, normX));

              const MARGIN_Y_BODY  = 0.40; 
              const MARGIN_Y_REACH = 0.25; 

              const currentMarginY = MARGIN_Y_BODY + normX * (MARGIN_Y_REACH - MARGIN_Y_BODY);
              const activeY = 1.0 - (currentMarginY * 2);

              let normY = (py - currentMarginY) / activeY;
              normY = Math.max(0, Math.min(1, normY));

              const [sx, sy] = smoothPointer(pState, normX, normY, performance.now() / 1000)
              pointerRef.current?.({ x: sx, y: sy })
            } else {
              clearTimeout(hideTimers[activeLabel]); hideTimers[activeLabel] = null
              wasActive[activeLabel] = false; pointerRef.current?.(null)
            }
          } else {
            if (!hideTimers[activeLabel]) {
              hideTimers[activeLabel] = setTimeout(() => {
                hideTimers[activeLabel] = null; wasActive[activeLabel] = false; pointerRef.current?.(null)
              }, CURSOR_HIDE_DELAY_MS)
            }
          }
        } else {
          if (activeLabel) { clearTimeout(hideTimers[activeLabel]); hideTimers[activeLabel] = null }
          pointerRef.current?.(null)
        }
      } catch (e) {
        pointerRef.current?.(null)
      }

      // 안 보이는 손 리셋
      const seen = new Set(handed.map(h => h?.label).filter(Boolean))
      for (const lbl of ['Left', 'Right']) {
        if (!seen.has(lbl)) {
          clearTimeout(hideTimers[lbl]); hideTimers[lbl] = null
          resetPointerState(pointerStates[lbl])
          wasActive[lbl] = false; wasPointing[lbl] = false; wasPinching[lbl] = false
          gestureStates[lbl] = makeGestureState(); palmBufs[lbl].length = 0
          lastSwipeDirs[lbl] = null; okNeedsOpen[lbl] = false
          
          stableFingers[lbl] = { count: 0, frames: 0 }
          pinchScroll[lbl] = { anchorX: null, active: false }
        }
      }

      // ── 제스처 인식 및 UI 전달 데이터 가공 ──────────────────────────────────
      const handData = {}
      const frameNow = performance.now()

      for (let i = 0; i < lms.length; i++) {
        const lm = lms[i]
        if (!_isValidLandmarks(lm)) continue
        if (_palmSize(lm) < MIN_PALM_SIZE) continue
        const mpLabel = handed[i]?.label || 'Right'
        const side    = mpLabel === 'Left' ? 'right' : 'left'

        const rpx = (lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 4
        const rpy = (lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 4
        palmBufs[mpLabel].push({ x: rpx, y: rpy, t: frameNow })
        const cutoff = frameNow - SWIPE_WINDOW_MS
        while (palmBufs[mpLabel].length && palmBufs[mpLabel][0].t < cutoff)
          palmBufs[mpLabel].shift()

        const pinching = _isPinching(lm, wasPinching[mpLabel])
        wasPinching[mpLabel] = pinching
        if (!pinching) okNeedsOpen[mpLabel] = false

        let scrollDx = 0
        if (pinching) {
          if (!pinchScroll[mpLabel].active) {
            pinchScroll[mpLabel].active = true
            pinchScroll[mpLabel].anchorX = rpx
          } else {
            scrollDx = (rpx - pinchScroll[mpLabel].anchorX) * 2.0 
            pinchScroll[mpLabel].anchorX = rpx
          }
        } else {
          pinchScroll[mpLabel].active = false
        }

        let gesture = null
        const swipe = _detectSwipe(palmBufs[mpLabel], lastSwipes[mpLabel], lastSwipeDirs[mpLabel], lm, camAR)
        if (swipe) {
          lastSwipes[mpLabel] = frameNow; lastSwipeDirs[mpLabel] = swipe
          palmBufs[mpLabel].length = 0; gestureStates[mpLabel].candidate = null; gestureStates[mpLabel].count = 0
          gesture = swipe
        } else {
          const raw = pinching ? 'ok' : _classifyStaticNoPinch(lm)
          const blocked = (raw === 'ok' && okNeedsOpen[mpLabel]) ? null : raw
          gesture = _confirmStatic(gestureStates[mpLabel], blocked)
        }
        if (gesture === 'ok') okNeedsOpen[mpLabel] = true

        const currentFingers = _countFingers(lm)
        if (stableFingers[mpLabel].count === currentFingers) {
          stableFingers[mpLabel].frames++
        } else {
          stableFingers[mpLabel].count = currentFingers
          stableFingers[mpLabel].frames = 1
        }
        const uiStableCount = stableFingers[mpLabel].frames >= STABLE_FRAMES_REQ ? stableFingers[mpLabel].count : null

        handData[side] = {
          gesture,
          finger_count:   currentFingers,
          stable_fingers: uiStableCount, 
          scroll_dx:      scrollDx,      
          is_pinching:    pinching,      
          pinch_distance: +_dist3d(lm[4], lm[8]).toFixed(4),
          is_pointing:    _isPointing(lm) || _isThumbIndexOpen(lm),
        }
      }

      const fired    = Object.values(handData).map(d => d.gesture).filter(Boolean)
      const dominant = fired.length
        ? fired.reduce((a, b) => (_GESTURE_PRIORITY[a] ?? 0) >= (_GESTURE_PRIORITY[b] ?? 0) ? a : b) : null

      gestureRef.current?.({
        hands:         { left: handData.left ?? null, right: handData.right ?? null },
        total_fingers: Object.values(handData).reduce((s, d) => s + d.finger_count, 0),
        gesture:       dominant,
      })

      if (pipCanvasRef?.current && video) {
        try { _drawPip(pipCanvasRef.current, video, lms, handed) } catch {}
      }
    }

    let inflightWatchdog = null
    const loop = () => {
      if (!active) return
      const now   = performance.now()
      const ready = !inflight && video && video.readyState >= 2 && hands &&
                    now - lastSent >= 1000 / MAX_FPS
      if (ready) {
        inflight = true; lastSent = now
        inflightWatchdog = setTimeout(() => { inflight = false }, 3000)
        hands.send({ image: video }).catch(err => {
          clearTimeout(inflightWatchdog); inflight = false
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
        if (video.videoWidth && video.videoHeight) camAR = video.videoWidth / video.videoHeight

        hands = new Hands({ locateFile: (f) => `${MP_BASE}${f}` })
        hands.setOptions({
          maxNumHands: 2, modelComplexity: 0, minDetectionConfidence: 0.6, minTrackingConfidence: 0.5,
        })
        hands.onResults(handleResults)
        loop()
      } catch (err) {}
    }

    setup()

    return () => {
      active = false; clearTimeout(inflightWatchdog); clearTimeout(hideTimers.Left); clearTimeout(hideTimers.Right)
      if (rafId) cancelAnimationFrame(rafId)
      try { hands?.close?.() } catch {}
      stream?.getTracks().forEach(t => t.stop())
      if (videoRef) videoRef.current = null
    }
  }, [enabled])
}