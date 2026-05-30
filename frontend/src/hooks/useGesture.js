import { useEffect, useRef } from 'react'
import { Hands } from '@mediapipe/hands'

// ── 카메라 설정 ──────────────────────────────────────────────────────────────
const CAM_W   = 640
const CAM_H   = 480
const MAX_FPS = 20
// 임계값 튜닝 기준 비율 (4:3). 실제 카메라 비율이 다르면 자동 보정됨.
const AR_REF  = CAM_W / CAM_H   // ≈ 1.333

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
// 가리키는 동작용 — 자연스럽게 살짝 굽은 검지도 인식
const EXTENSION_MARGIN_POINT       = 1.08
// 히스테리시스: 이미 가리키는 중이면 더 관대 (잠깐 굽혀도 유지)
const EXTENSION_MARGIN_POINT_HOLD  = 1.00
const EXTENSION_MARGIN_FOLD_HOLD   = 1.18  // 다른 손가락 "안 펴짐" 판정도 완화

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

// 손목(0) → 중지 MCP(9) 거리 — 멀수록 작아지는 손 크기 지표
// 카메라 비율에 무관하게 비교하려면 x를 보정해야 하지만,
// 여기선 단순 임계값 비교이므로 2D 그대로 사용
const MIN_PALM_SIZE = 0.10  // 이 이하면 너무 멀리 있는 손으로 간주

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

// 커서 활성 A: 검지만 핀 (엄지 무관)
function _isPointing(lm) {
  return (
     _isFingerExtended(lm, 8,  6, EXTENSION_MARGIN_POINT) &&
    !_isFingerExtended(lm, 12, 10) &&
    !_isFingerExtended(lm, 16, 14) &&
    !_isFingerExtended(lm, 20, 18)
  )
}

// 커서 활성 B: 엄지+검지 동시에 핀 (핀치 전 준비 자세)
function _isThumbIndexOpen(lm) {
  return (
    _isThumbExtended(lm)                                  &&
     _isFingerExtended(lm, 8,  6, EXTENSION_MARGIN_POINT) &&
    !_isFingerExtended(lm, 12, 10)                        &&
    !_isFingerExtended(lm, 16, 14)                        &&
    !_isFingerExtended(lm, 20, 18)
  )
}

// 히스테리시스: 이미 가리키는 중일 때 검사 — 검지는 더 관대하게, 나머지는 살짝 펴져도 허용
// (잠깐 손가락이 굽거나 떨려도 커서가 끊기지 않게 함)
function _isPointingHold(lm) {
  const indexOK = _isFingerExtended(lm, 8, 6, EXTENSION_MARGIN_POINT_HOLD)
  const otherFolded =
    !_isFingerExtended(lm, 12, 10, EXTENSION_MARGIN_FOLD_HOLD) &&
    !_isFingerExtended(lm, 16, 14, EXTENSION_MARGIN_FOLD_HOLD) &&
    !_isFingerExtended(lm, 20, 18, EXTENSION_MARGIN_FOLD_HOLD)
  return indexOK && otherFolded
}

// 핀치: 엄지(4) ↔ 검지(8) 거리를 손 크기(팜 사이즈) 대비 비율로 판정
// - 3D z 기반 고정 임계값은 카메라 각도에 따라 z 추정이 불안정해 오탈락이 많음
// - 팜 크기 정규화 비율은 손이 멀거나 가깝거나, 각도가 달라도 일관된 값 유지
// - 히스테리시스: 진입 임계(더 엄격) vs 유지 임계(더 관대) → 각도 변화에서 끊김 방지
// - 주먹 오인식 차단은 _isFingerExtended(8, 6, 0.8) 유지 (검지가 조금이라도 펴져야 함)
const PINCH_RATIO_ENTER = 0.30   // 팜 대비 30% 이내: 핀치 진입
const PINCH_RATIO_EXIT  = 0.44   // 팜 대비 44% 이내: 핀치 유지 (히스테리시스)

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

// 카메라 활성 구역 마진 (손바닥 중심 기준 → 손가락 끝 오프셋 보정 포함)
const CAM_MARGIN_L   = 0.20   // 좌: 손 측면 오프셋 보정
const CAM_MARGIN_R   = 0.20   // 우: 손 측면 오프셋 보정
const CAM_MARGIN_TOP = 0.25   // 상: 기본 10% + 손가락 끝↔손바닥 중심 차이 15%
const CAM_MARGIN_BOT = 0.10
const CAM_ACTIVE_X   = 1.0 - CAM_MARGIN_L - CAM_MARGIN_R     // 0.60
const CAM_ACTIVE_Y   = 1.0 - CAM_MARGIN_TOP - CAM_MARGIN_BOT // 0.65

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

// 핀치 제외 정적 분류 — 루프에서 핀치를 별도 체크한 뒤 나머지 분류에 사용
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
const SWIPE_COOLDOWN_REVERSE = 1500  // 직전 반대 방향 쿨다운 (복귀 동작 오인식 방지)
const SWIPE_WINDOW_MS        = 700   // 버퍼 유지 시간
const SWIPE_MIN_FRAMES       = 4     // 트림 후 최소 프레임 수
const SWIPE_STEP_THRESHOLD   = 0.004 // 프레임 간 이동 최소치 (정지 판정)

// 좌우 — x 변위 최소치 / y 최대 허용 오차
const SWIPE_LR_MIN_X     = 0.10
const SWIPE_LR_MAX_Y     = 0.08
// 상하 — y 변위 최소치 / x 최대 허용 오차
const SWIPE_UD_MIN_Y     = 0.09
const SWIPE_UD_MAX_X     = 0.08
// 직선도: 순변위 / 총경로 길이
const SWIPE_STRAIGHTNESS = 0.50
// 방향 일관성: 같은 방향 스텝 비율
const SWIPE_CONSISTENCY  = 0.65
// 최소 속도: 정규화 단위/초 (느린 드리프트 차단)
const SWIPE_MIN_SPEED    = 0.25

const _SWIPE_REVERSE = {
  swipe_left: 'swipe_right', swipe_right: 'swipe_left',
  swipe_up:   'swipe_down',  swipe_down:  'swipe_up',
}

// 버퍼 앞뒤의 정지 프레임 제거 — 스와이프 전 대기·후 감속 구간이 분석을 희석하는 것을 방지
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

// X는 화면 미러링 반영: 카메라 dx<0 = 사용자 기준 오른쪽 → swipe_right
// camAR: 실제 카메라 비율(width/height). AR_REF 기준으로 x를 물리 단위로 보정.
function _detectSwipe(buf, lastSwipeT, lastSwipeDir, lm, camAR) {
  if (!_isOpenForSwipe(lm)) return null

  // 정지 구간 제거 후 분석
  const a = _trimBuf(buf)
  if (a.length < SWIPE_MIN_FRAMES) return null

  // 정규화 x를 물리 단위로 변환 — 카메라 비율이 달라도 임계값이 일정한 물리 거리에 대응
  // wide(16:9): camAR/AR_REF > 1 → 같은 normalized dx = 더 넓은 물리 이동 → 스케일 업
  // tall(9:16): camAR/AR_REF < 1 → 같은 normalized dx = 좁은 물리 이동 → 스케일 다운
  const xPhys = camAR / AR_REF

  const rawDx = a[a.length - 1].x - a[0].x
  const rawDy = a[a.length - 1].y - a[0].y
  const dx  = rawDx * xPhys   // 물리 단위 x 변위
  const dy  = rawDy            // y는 그대로
  const adx = Math.abs(dx), ady = Math.abs(dy)
  const netDist = Math.sqrt(dx * dx + dy * dy)

  // ① 방향 후보 판별 (물리 단위 기준)
  let candidate = null
  if (adx >= ady && adx >= SWIPE_LR_MIN_X && ady <= SWIPE_LR_MAX_Y) {
    // 방향 일관성은 부호만 보므로 raw x step 그대로 사용
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

  // ② 방향별 쿨다운
  const isReverse = lastSwipeDir && _SWIPE_REVERSE[lastSwipeDir] === candidate
  const cooldown  = isReverse ? SWIPE_COOLDOWN_REVERSE : SWIPE_COOLDOWN_MS
  if (performance.now() - lastSwipeT < cooldown) return null

  // ③ 속도 게이트 (물리 단위)
  const dt = (a[a.length - 1].t - a[0].t) / 1000
  if (dt < 0.05 || netDist / dt < SWIPE_MIN_SPEED) return null

  // ④ 직선도 (물리 단위)
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

// ── MediaPipe 관절 연결선 (21개 랜드마크) ─────────────────────────────────────
const HAND_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],           // 엄지
  [0,5],[5,6],[6,7],[7,8],           // 검지
  [5,9],[9,10],[10,11],[11,12],      // 중지
  [9,13],[13,14],[14,15],[15,16],    // 약지
  [13,17],[17,18],[18,19],[19,20],   // 소지
  [0,17],[5,9],[9,13],[13,17],       // 손바닥
]

// PiP 캔버스에 영상 + 랜드마크를 그린다 (미러 반전 포함)
function _drawPip(canvas, video, lms, handed) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const vw = video.videoWidth, vh = video.videoHeight
  if (!vw || !vh) return
  if (canvas.width !== vw || canvas.height !== vh) {
    canvas.width  = vw
    canvas.height = vh
  }
  // 미러 반전 영상
  ctx.save()
  ctx.translate(vw, 0)
  ctx.scale(-1, 1)
  ctx.drawImage(video, 0, 0)
  ctx.restore()

  // 각 손 랜드마크
  for (let hi = 0; hi < lms.length; hi++) {
    const lm    = lms[hi]
    if (!lm || lm.length < 21) continue
    const isRight = handed[hi]?.label === 'Right'  // MP 기준 (사용자 왼손)

    // 연결선
    ctx.lineWidth   = 2.5
    ctx.strokeStyle = isRight ? 'rgba(100,160,255,0.9)' : 'rgba(80,220,130,0.9)'
    for (const [a, b] of HAND_CONNECTIONS) {
      ctx.beginPath()
      ctx.moveTo((1 - lm[a].x) * vw, lm[a].y * vh)
      ctx.lineTo((1 - lm[b].x) * vw, lm[b].y * vh)
      ctx.stroke()
    }

    // 관절 점
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
    let camAR    = AR_REF   // 카메라 실제 비율 (열린 후 갱신)

    // ── 포인터 상태 ──────────────────────────────────────────────────────────
    const pointerStates = { Left: makePointerState(), Right: makePointerState() }
    const wasActive     = { Left: false, Right: false }
    // 한 번 가리키기 시작했으면 잠깐 흔들려도 끊기지 않게 — 히스테리시스
    const wasPointing   = { Left: false, Right: false }
    const CURSOR_HIDE_DELAY_MS = 350
    const hideTimers    = { Left: null, Right: null }

    // ── 제스처 상태 ──────────────────────────────────────────────────────────
    const gestureStates = { Left: makeGestureState(), Right: makeGestureState() }
    const palmBufs      = { Left: [], Right: [] }
    const lastSwipes    = { Left: -Infinity, Right: -Infinity }
    const lastSwipeDirs = { Left: null, Right: null }
    // ok 발화 후 손을 한 번 펴야 다음 ok 허용 (같은 자리 연속 발화 방지)
    const okNeedsOpen   = { Left: false, Right: false }
    // 핀치 히스테리시스 — 진입/유지 임계를 구분해 각도 변화에서 끊기지 않게 함
    const wasPinching   = { Left: false, Right: false }

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
        if (activeIdx >= 0 && _isValidLandmarks(lms[activeIdx]) &&
            _palmSize(lms[activeIdx]) >= MIN_PALM_SIZE) {
          const lm       = lms[activeIdx]
          // 히스테리시스: 이미 가리키는 중이면 더 관대한 조건으로 유지 → 끊김 감소
          const pointing = wasPointing[activeLabel]
            ? (_isPointingHold(lm) || _isPointing(lm) || _isThumbIndexOpen(lm))
            : (_isPointing(lm)     || _isThumbIndexOpen(lm))
          // 핀치도 히스테리시스 — 포인터 섹션에서는 wasPinching을 미리 읽고, 제스처 섹션에서 갱신
          const pinching = !pointing && _isPinching(lm, wasPinching[activeLabel])
          wasPointing[activeLabel] = pointing

          // 신뢰도 낮은 감지 무시 (화면 가장자리, 손 일부 잘림 등)
          const handScore = handed[activeIdx]?.score ?? 1
          if (handScore < 0.7) {
            if (!hideTimers[activeLabel]) {
              hideTimers[activeLabel] = setTimeout(() => {
                hideTimers[activeLabel] = null
                wasActive[activeLabel]  = false
                pointerRef.current?.(null)
              }, CURSOR_HIDE_DELAY_MS)
            }
          } else if (pointing || pinching) {
            clearTimeout(hideTimers[activeLabel])
            hideTimers[activeLabel] = null

            // 손목(0)↔중지MCP(9) 중간점 — 손 자세에 가장 안정적
            const px = (lm[0].x + lm[9].x) / 2
            const py = (lm[0].y + lm[9].y) / 2

            if (Number.isFinite(px) && Number.isFinite(py)) {
              // 재활성화 시 OneEuro 리셋 — 이전 상태가 남아 있으면 커서 점프 발생
              if (!wasActive[activeLabel]) resetPointerState(pointerStates[activeLabel])
              wasActive[activeLabel] = true

              // 절대 선형 매핑 — 방향별 마진 개별 적용
              const normX = Math.max(0, Math.min(1, (px - CAM_MARGIN_L)   / CAM_ACTIVE_X))
              const normY = Math.max(0, Math.min(1, (py - CAM_MARGIN_TOP) / CAM_ACTIVE_Y))
              const [sx, sy] = smoothPointer(
                pointerStates[activeLabel], normX, normY, performance.now() / 1000
              )
              pointerRef.current?.({ x: sx, y: sy })
            } else {
              clearTimeout(hideTimers[activeLabel])
              hideTimers[activeLabel] = null
              wasActive[activeLabel]  = false
              pointerRef.current?.(null)
            }
          } else {
            if (!hideTimers[activeLabel]) {
              hideTimers[activeLabel] = setTimeout(() => {
                hideTimers[activeLabel] = null
                wasActive[activeLabel]  = false
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
          wasActive[lbl]        = false
          wasPointing[lbl]      = false
          wasPinching[lbl]      = false
          gestureStates[lbl]    = makeGestureState()
          palmBufs[lbl].length  = 0
          lastSwipeDirs[lbl]    = null
          okNeedsOpen[lbl]      = false
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
        if (_palmSize(lm) < MIN_PALM_SIZE) continue   // 너무 먼 손 무시
        const mpLabel = handed[i]?.label || 'Right'
        const side    = mpLabel === 'Left' ? 'right' : 'left'

        // 원시 손바닥 중심 — 앵커 변환 없이 절대 위치 (스와이프 추적용)
        const rpx = (lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 4
        const rpy = (lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 4
        palmBufs[mpLabel].push({ x: rpx, y: rpy, t: frameNow })
        const cutoff = frameNow - SWIPE_WINDOW_MS
        while (palmBufs[mpLabel].length && palmBufs[mpLabel][0].t < cutoff)
          palmBufs[mpLabel].shift()

        // 핀치 히스테리시스 적용 — 이전 프레임 핀치 여부를 넘겨 유지 임계 사용
        const pinching = _isPinching(lm, wasPinching[mpLabel])
        wasPinching[mpLabel] = pinching

        // ok 리셋 플래그: 핀치 해제되면 다시 허용
        if (!pinching) okNeedsOpen[mpLabel] = false

        let gesture = null
        const swipe = _detectSwipe(palmBufs[mpLabel], lastSwipes[mpLabel], lastSwipeDirs[mpLabel], lm, camAR)
        if (swipe) {
          lastSwipes[mpLabel]              = frameNow
          lastSwipeDirs[mpLabel]           = swipe
          palmBufs[mpLabel].length         = 0
          gestureStates[mpLabel].candidate = null
          gestureStates[mpLabel].count     = 0
          gesture = swipe
        } else {
          // _classifyStatic 내부의 _isPinching도 히스테리시스 적용
          const raw     = pinching ? 'ok' : _classifyStaticNoPinch(lm)
          const blocked = (raw === 'ok' && okNeedsOpen[mpLabel]) ? null : raw
          gesture = _confirmStatic(gestureStates[mpLabel], blocked)
        }

        if (gesture === 'ok') okNeedsOpen[mpLabel] = true

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

      // PiP 캔버스에 인식 영상 + 관절 그리기
      if (pipCanvasRef?.current && video) {
        try { _drawPip(pipCanvasRef.current, video, lms, handed) } catch {}
      }
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

        // 실제 카메라 비율 측정 — 이후 모든 제스처 계산에 적용
        if (video.videoWidth && video.videoHeight) {
          camAR = video.videoWidth / video.videoHeight
          console.log(`[useGesture] 카메라 비율: ${video.videoWidth}×${video.videoHeight} (AR=${camAR.toFixed(3)})`)
        }

        hands = new Hands({ locateFile: (f) => `${MP_BASE}${f}` })
        hands.setOptions({
          maxNumHands:            2,
          modelComplexity:        0,
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
