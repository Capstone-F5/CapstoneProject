// LLM 대화 음성(채팅 패널의 응답 읽기) 재생 속도(배속).
//
// - 관리자 설정(키오스크 설정 → 음성 안내 속도): 기본 배속·최소·최대. localStorage `kioskDevSettings`의 `tts`에서 읽는다
//   (백엔드 /api/settings/kiosk가 내려주고 settingsService.applyKioskSettingsToRuntime이 저장한다).
// - 손님이 하단 컨트롤 바(음성인식 ON일 때)에서 고른 배속: localStorage `kioskTtsSpeed`. 항상 [최소, 최대] 안으로 자르고, 새 손님(세션 초기화)이면 지운다.
// - 소리의 높낮이는 그대로 두고 속도만 바꾼다(preservesPitch).
// 순수 계산(clampSpeed·resolveSpeed·stepSpeed·normalizeLimits)은 DOM 없이 테스트한다(frontend/tests/ttsSpeed.test.js).

export const SPEED_DEFAULTS = { default_speed: 1.0, min_speed: 0.7, max_speed: 1.5 }
export const SPEED_BOUNDS = { minLo: 0.5, minHi: 1.0, maxLo: 1.0, maxHi: 2.0 }   // 백엔드 kiosk_settings._sanitize와 같은 범위
export const SPEED_STEP = 0.1

const CHOSEN_KEY = 'kioskTtsSpeed'
const CHANGE_EVENT = 'kiosk-tts-speed-change'
const SETTINGS_KEY = 'kioskDevSettings'

const round2 = (v) => Math.round(v * 100) / 100
const num = (v, fallback) => {
  // 숫자 또는 숫자 문자열만 인정한다(Number([])===0, Number(true)===1 같은 JS 변환에 속지 않게 — 백엔드 float()와 같은 판정)
  if (!(typeof v === 'number' || (typeof v === 'string' && v.trim() !== ''))) return fallback
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

export function clampSpeed(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

/** 설정(tts 섹션)에서 { min, max, def }를 만든다. 잘못된 값은 기본값으로, 범위는 백엔드와 같게 자른다. */
export function normalizeLimits(tts) {
  const t = tts && typeof tts === 'object' ? tts : {}
  const min = round2(clampSpeed(num(t.min_speed, SPEED_DEFAULTS.min_speed), SPEED_BOUNDS.minLo, SPEED_BOUNDS.minHi))
  const max = round2(clampSpeed(num(t.max_speed, SPEED_DEFAULTS.max_speed), SPEED_BOUNDS.maxLo, SPEED_BOUNDS.maxHi))
  const def = round2(clampSpeed(num(t.default_speed, SPEED_DEFAULTS.default_speed), min, max))
  return { min, max, def }
}

/** 손님이 고른 값(없거나 숫자가 아니면 null)을 [min, max] 안의 실제 배속으로 바꾼다. 고른 적이 없으면 기본 배속. */
export function resolveSpeed(chosen, limits) {
  const n = num(chosen, null)
  return n === null ? limits.def : round2(clampSpeed(n, limits.min, limits.max))
}

/** 0.1 단위 눈금으로 한 칸 올리거나(dir=+1) 내린다(dir=-1). 0.75처럼 눈금 밖 값에서도 시작할 수 있고, 한계값에는 항상 닿는다. */
export function stepSpeed(current, dir, limits) {
  const tenths = Math.round(current * 10) + (dir > 0 ? 1 : -1)
  return round2(clampSpeed(tenths / 10, limits.min, limits.max))
}

// ── 브라우저 런타임 ──────────────────────────────────────────────────────────

const hasWindow = () => typeof window !== 'undefined'

export function getSpeedLimits() {
  if (!hasWindow()) return normalizeLimits(null)
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY)
    return normalizeLimits(raw ? JSON.parse(raw).tts : null)
  } catch {
    return normalizeLimits(null)
  }
}

/** 지금 적용할 배속: 손님이 고른 값(범위 안으로 보정) 또는 기본 배속. */
export function getTtsSpeed() {
  const limits = getSpeedLimits()
  if (!hasWindow()) return limits.def
  try {
    return resolveSpeed(window.localStorage.getItem(CHOSEN_KEY), limits)
  } catch {
    return limits.def
  }
}

const emit = () => { try { window.dispatchEvent(new Event(CHANGE_EVENT)) } catch {} }

export function setTtsSpeed(v) {
  const speed = resolveSpeed(v, getSpeedLimits())
  try { window.localStorage.setItem(CHOSEN_KEY, String(speed)) } catch {}
  emit()
  return speed
}

/** 새 손님: 고른 배속을 지우고 기본 배속으로 돌아간다. */
export function resetTtsSpeed() {
  try { window.localStorage.removeItem(CHOSEN_KEY) } catch {}
  emit()
  return getTtsSpeed()
}

export function stepTtsSpeed(dir) {
  return setTtsSpeed(stepSpeed(getTtsSpeed(), dir, getSpeedLimits()))
}

/** 오디오 요소에 지금 적용할 배속(손님이 고른 값 또는 기본)을 적용한다. 재생 시작 전·재생 중 어느 때나 호출할 수 있다. */
export function applySpeed(audio) {
  setAudioSpeed(audio, getTtsSpeed())
}

/** 오디오 요소에 지정한 배속을 적용한다(소리 높낮이는 유지). 설정 페이지의 미리 듣기가 쓴다. */
export function setAudioSpeed(audio, speed) {
  if (!audio) return
  try {
    audio.defaultPlaybackRate = speed
    audio.playbackRate = speed
    audio.preservesPitch = true
    audio.webkitPreservesPitch = true
    audio.mozPreservesPitch = true
  } catch { /* 일부 환경에서 속성 설정이 막혀도 재생은 계속한다 */ }
}

/**
 * 배속이 바뀌는 모든 경우(손님 조작·초기화·관리자 설정 변경·다른 탭)에 cb(현재 배속, 한계)를 부른다. 해제 함수를 돌려준다.
 */
export function subscribeTtsSpeed(cb) {
  if (!hasWindow()) return () => {}
  const handler = () => cb(getTtsSpeed(), getSpeedLimits())
  const onStorage = (e) => { if (e.key === CHOSEN_KEY || e.key === SETTINGS_KEY) handler() }
  window.addEventListener(CHANGE_EVENT, handler)
  window.addEventListener('kiosk-dev-settings-changed', handler)   // 관리자가 범위·기본값을 바꿈
  window.addEventListener('storage', onStorage)
  return () => {
    window.removeEventListener(CHANGE_EVENT, handler)
    window.removeEventListener('kiosk-dev-settings-changed', handler)
    window.removeEventListener('storage', onStorage)
  }
}
