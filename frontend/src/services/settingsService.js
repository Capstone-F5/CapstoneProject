// 대기화면 배경 슬라이드 목록 및 키오스크 개발자 설정(마이크 감도 · 접근 감지) 동기화 서비스
const API_BASE = import.meta.env.VITE_API_URL ?? ''

const FALLBACK_IMAGES = ['/bg.jpg']
const CHANNEL_NAME = 'kiosk-dev-settings'

export const DEFAULT_KIOSK_SETTINGS = {
  debug_mode: false,
  mic: {
    preset: 'standard',
    auto_gain_control: false,
    min_speech_rms: 0.018,
    snr_margin: 2.0,
    min_active_ms: 120,
    vad_positive_threshold: 0.80,
    vad_negative_threshold: 0.45,
    vad_redemption_frames: 8,
    no_speech_threshold: 0.65,
    logprob_threshold: -1.0,
    short_word_logprob_threshold: -1.35,
    compression_threshold: 2.4,
    domain_guard_enabled: true,
    barge_in_enabled: false,
  },
  // LLM 대화 음성 배속 — 기본/최소/최대 (utils/ttsSpeed.js, 백엔드 kiosk_settings.py와 같은 범위)
  tts: {
    default_speed: 1.0,
    min_speed: 0.7,
    max_speed: 1.5,
  },
  approach: {
    preset: 'standard',
    enabled: true,
    confidence_threshold: 0.50,
    wheelchair_confidence: 0.50,
    person_confidence: 0.50,
    white_cane_confidence: 0.50,
    min_box_h: 0.15,
    frame_interval_ms: 500,
    confirm_window: 4,
    confirm_hits: 3,
    rearm_absent_frames: 6,
    announcement_interval_sec: 10.0,
    max_announcements: 3,
    motion_gate_enabled: true,
    motion_threshold: 0.025,
    motion_keepalive_sec: 4.0,
  },
  gesture: {
    preset: 'standard',
    enabled: true,
    min_palm_size: 0.08,
    detection_confidence: 0.65,
    tracking_confidence: 0.50,
    target_fps: 15,
    cam_width: 640,
    cam_height: 480,
    margin_left: 0.20,
    margin_right: 0.20,
    margin_top: 0.25,
    margin_bottom: 0.10,
    edge_pad: 0.05,
    margin_x: 0.20,
    margin_bot: 0.10,
  },
}

export async function fetchStartScreenImages() {
  try {
    const res = await fetch(`${API_BASE}/api/settings/start-screen-images`)
    if (!res.ok) throw new Error(`start screen images fetch failed (${res.status})`)
    const data = await res.json()
    const urls = data.map(i => i.image_url).filter(Boolean)
    return urls.length ? urls : FALLBACK_IMAGES
  } catch (e) {
    console.error('[settingsService] 대기화면 이미지 조회 실패, 기본값 사용:', e)
    return FALLBACK_IMAGES
  }
}

/**
 * 키오스크 개발자 설정을 브라우저 localStorage 및 전역 객체에 즉시 반영하고
 * 다른 탭(열려 있는 키오스크 화면)에 BroadcastChannel로 전파한다.
 */
export function applyKioskSettingsToRuntime(settings, broadcast = true) {
  if (typeof window === 'undefined' || !settings) return
  try {
    const merged = {
      debug_mode: Boolean(settings.debug_mode ?? DEFAULT_KIOSK_SETTINGS.debug_mode),
      mic: { ...DEFAULT_KIOSK_SETTINGS.mic, ...(settings.mic || {}) },
      tts: { ...DEFAULT_KIOSK_SETTINGS.tts, ...(settings.tts || {}) },
      approach: { ...DEFAULT_KIOSK_SETTINGS.approach, ...(settings.approach || {}) },
      gesture: { ...DEFAULT_KIOSK_SETTINGS.gesture, ...(settings.gesture || {}) },
    }
    window.localStorage.setItem('kioskDevSettings', JSON.stringify(merged))

    // AudioEnergyGate & AGC 오버라이드 포맷으로 변환해 저장
    const gateConfig = {
      autoGainControl: Boolean(merged.mic.auto_gain_control),
      minSpeechRms: Number(merged.mic.min_speech_rms),
      snrMargin: Number(merged.mic.snr_margin),
      minActiveMs: Number(merged.mic.min_active_ms),
      vadPositiveThreshold: Number(merged.mic.vad_positive_threshold),
      vadNegativeThreshold: Number(merged.mic.vad_negative_threshold),
      vadRedemptionFrames: Number(merged.mic.vad_redemption_frames),
    }
    window.localStorage.setItem('sttGateConfig', JSON.stringify(gateConfig))
    window.__sttGateConfig = gateConfig

    // Barge-in 설정 동기화
    window.localStorage.setItem('bargeIn', merged.mic.barge_in_enabled ? '1' : '0')
    window.dispatchEvent(new Event('kiosk-bargein-change'))

    // Gesture (MediaPipe 온디바이스) 설정 동기화
    window.localStorage.setItem('kioskGestureConfig', JSON.stringify(merged.gesture))
    window.__kioskGestureConfig = merged.gesture
    window.dispatchEvent(new CustomEvent('kiosk-gesture-config-changed', { detail: merged.gesture }))

    window.dispatchEvent(new CustomEvent('kiosk-dev-settings-changed', { detail: merged }))

    if (broadcast && typeof BroadcastChannel !== 'undefined') {
      const bc = new BroadcastChannel(CHANNEL_NAME)
      bc.postMessage({ type: 'kiosk-settings-updated', settings: merged })
      bc.close()
    }
  } catch (e) {
    console.warn('[settingsService] 런타임 설정 적용 실패:', e)
  }
}

export function loadCachedKioskSettings() {
  if (typeof window === 'undefined') return DEFAULT_KIOSK_SETTINGS
  try {
    const raw = window.localStorage.getItem('kioskDevSettings')
    if (!raw) return DEFAULT_KIOSK_SETTINGS
    const parsed = JSON.parse(raw)
    return {
      debug_mode: Boolean(parsed.debug_mode ?? DEFAULT_KIOSK_SETTINGS.debug_mode),
      mic: { ...DEFAULT_KIOSK_SETTINGS.mic, ...(parsed.mic || {}) },
      tts: { ...DEFAULT_KIOSK_SETTINGS.tts, ...(parsed.tts || {}) },
      approach: { ...DEFAULT_KIOSK_SETTINGS.approach, ...(parsed.approach || {}) },
      gesture: { ...DEFAULT_KIOSK_SETTINGS.gesture, ...(parsed.gesture || {}) },
    }
  } catch {
    return DEFAULT_KIOSK_SETTINGS
  }
}

export function subscribeKioskSettings(onUpdate) {
  if (typeof window === 'undefined') return () => {}

  const handleCustom = (e) => {
    if (e.detail) onUpdate(e.detail)
  }
  const handleStorage = (e) => {
    if (e.key === 'kioskDevSettings' && e.newValue) {
      try {
        onUpdate(JSON.parse(e.newValue))
      } catch {}
    }
  }

  window.addEventListener('kiosk-dev-settings-changed', handleCustom)
  window.addEventListener('storage', handleStorage)

  let bc = null
  if (typeof BroadcastChannel !== 'undefined') {
    bc = new BroadcastChannel(CHANNEL_NAME)
    bc.onmessage = (msg) => {
      if (msg.data?.type === 'kiosk-settings-updated' && msg.data.settings) {
        applyKioskSettingsToRuntime(msg.data.settings, false)
      }
    }
  }

  return () => {
    window.removeEventListener('kiosk-dev-settings-changed', handleCustom)
    window.removeEventListener('storage', handleStorage)
    bc?.close()
  }
}

export async function fetchKioskSettings() {
  try {
    const res = await fetch(`${API_BASE}/api/settings/kiosk`)
    if (!res.ok) throw new Error(`kiosk settings fetch failed (${res.status})`)
    const data = await res.json()
    if (data?.settings) {
      applyKioskSettingsToRuntime(data.settings, false)
    }
    return data
  } catch (e) {
    console.warn('[settingsService] 키오스크 설정 조회 실패, 로컬 캐시 사용:', e)
    return {
      settings: loadCachedKioskSettings(),
      defaults: DEFAULT_KIOSK_SETTINGS,
    }
  }
}

export async function saveKioskSettings(payload) {
  const res = await fetch(`${API_BASE}/api/settings/kiosk`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`설정 저장 실패 (${res.status})`)
  const data = await res.json()
  if (data?.settings) {
    applyKioskSettingsToRuntime(data.settings, true)
  }
  return data
}

export async function resetKioskSettings() {
  const res = await fetch(`${API_BASE}/api/settings/kiosk/reset`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`설정 초기화 실패 (${res.status})`)
  const data = await res.json()
  if (data?.settings) {
    applyKioskSettingsToRuntime(data.settings, true)
  }
  return data
}

export async function fetchKioskDiagnosticLogs(limit = 30) {
  const res = await fetch(`${API_BASE}/api/settings/kiosk/logs?limit=${limit}`)
  if (!res.ok) throw new Error(`로그 조회 실패 (${res.status})`)
  return res.json()
}
