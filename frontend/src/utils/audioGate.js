// STT 전송 전 음향 에너지(RMS · SNR · 지속시간) 게이트 및 마이크 AGC(자동 이득 제어) 차단.
//
// 왜 필요한가:
// 1) @ricky0123/vad-web 의 MicVAD는 getUserMedia 호출 시 autoGainControl: true 를 강제한다.
//    키오스크 앞에 아무도 말하지 않는 동안 브라우저 AGC가 마이크 증폭률을 최대로 올리면,
//    2~5m 밖의 주변 테이블 대화나 매장 배경 음악(BGM) 보컬이 근접 발화 크기로 증폭되어 VAD를 통과한다.
// 2) Silero VAD는 파형이 사람 목소리처럼 생겼는지만 판별할 뿐 절대 음량(RMS)이나 배경 대비 신호비(SNR)를
//    따지지 않으므로, onSpeechEnd(audio)에서 실제 음향 에너지를 검사해 원거리 대화·배경 음악·충격음을 걸러낸다.

export const GATE_DEFAULTS = {
  sampleRate: 16000,
  windowMs: 30,             // 30ms(480샘플) 단위로 에너지 분석
  minDurationMs: 180,       // 전체 오디오 최소 길이
  maxDurationMs: 18000,     // 18초 초과 연속 잡음/음악 녹음 차단
  minSpeechRms: 0.018,      // 근접 발화 최소 RMS 하한 (AGC OFF 기준 원거리 일상 대화 차단)
  snrMargin: 2.0,           // 배경 소음 바닥(Noise Floor) 대비 최소 배수 (+6dB 이상)
  minActiveMs: 120,         // 유효 음성 에너지가 유지되어야 하는 최소 시간 (박수·식기 달그락 등 충격음 차단)
  minNoiseFloor: 0.002,     // 소음 바닥 하한
  maxNoiseFloor: 0.06,      // 소음 바닥 상한 (큰 발화가 바닥값을 오염시키지 않도록 제한)
  floorAlpha: 0.15,         // 배경 소음 바닥 지수이동평균(EMA) 갱신 계수
  marginWindowCount: 10,    // 선행(preSpeechPad)/후행(redemption) 패딩에서 추출할 주변 배경 윈도우 수(각 300ms)
}

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v))
}

function percentile(sorted, p) {
  if (!sorted.length) return 0
  const idx = clamp(Math.floor(sorted.length * p), 0, sorted.length - 1)
  return sorted[idx]
}

export class AudioEnergyGate {
  constructor(opts = {}) {
    this.o = { ...GATE_DEFAULTS, ...opts }
    this.noiseFloor = 0.004   // 초기 배경 소음 바닥 (무음~조용한 실내 수준)
  }

  /** 런타임 설정 업데이트 (디버그 콘솔·캘리브레이션 용도) */
  configure(opts = {}) {
    this.o = { ...this.o, ...opts }
  }

  /**
   * VAD가 잘라낸 Float32Array(16kHz) 오디오 구간을 평가한다.
   * @param {Float32Array} audio 16kHz 모노 PCM 샘플 (-1.0 ~ 1.0)
   * @returns {{ pass: boolean, reason: string, metrics: object }}
   */
  evaluate(audio) {
    const o = this.o
    if (!audio || typeof audio.length !== 'number' || audio.length === 0) {
      return { pass: false, reason: 'empty', metrics: { durationMs: 0 } }
    }

    const durationMs = Math.round((audio.length / o.sampleRate) * 1000)
    if (durationMs < o.minDurationMs) {
      return { pass: false, reason: 'too_short', metrics: { durationMs } }
    }
    if (durationMs > o.maxDurationMs) {
      return { pass: false, reason: 'too_long', metrics: { durationMs } }
    }

    const winSize = Math.max(1, Math.floor((o.sampleRate * o.windowMs) / 1000))
    const winRms = []
    for (let start = 0; start + winSize <= audio.length; start += winSize) {
      let sumSq = 0
      for (let i = start; i < start + winSize; i++) {
        const s = audio[i]
        sumSq += s * s
      }
      winRms.push(Math.sqrt(sumSq / winSize))
    }

    if (winRms.length === 0) {
      return { pass: false, reason: 'too_short', metrics: { durationMs } }
    }

    const sorted = [...winRms].sort((a, b) => a - b)

    // 1) 선행(preSpeechPad)과 후행(redemption) 가장자리 윈도우에서 이 발화 전후의 주변 소음 레벨 추정
    const edgeN = Math.min(o.marginWindowCount, Math.floor(winRms.length / 4))
    let marginFloor
    if (edgeN >= 2) {
      const edges = [
        ...winRms.slice(0, edgeN),
        ...winRms.slice(winRms.length - edgeN),
      ].sort((a, b) => a - b)
      marginFloor = percentile(edges, 0.4)   // 가장자리 중 하위 40% 지점 (말소리가 살짝 걸친 프레임 배제)
    } else {
      marginFloor = percentile(sorted, 0.2)
    }

    const p20 = percentile(sorted, 0.2)
    const localFloor = Math.min(marginFloor, p20)

    // 2) 발화 활성 구간의 대표 RMS
    //    VAD는 말 앞뒤로 약 1.5초(preSpeechPad + redemption)의 무음 패딩을 붙이므로,
    //    "네", "응", "매장" 같은 짧은 발화(180~300ms = 6~10윈도우)는 전체 클립의 10~15%만 차지한다.
    //    따라서 최소 유효 발화 길이(minActiveMs, 기본 4윈도우=120ms) ~ 최대 10윈도우(300ms)의 핵심 구간 평균을 쓴다.
    const minActiveWindows = Math.max(1, Math.ceil(o.minActiveMs / o.windowMs))
    const coreCount = clamp(Math.round(sorted.length * 0.14), minActiveWindows, 10)
    const topSlice = sorted.slice(Math.max(0, sorted.length - coreCount))
    const activeRms = topSlice.reduce((a, b) => a + b, 0) / topSlice.length
    const peakRms = sorted[sorted.length - 1]

    // 3) 유효 기준 바닥: 지속적인 배경 음악/소음(localFloor 자체가 높음)과 조용한 방 모두 대응
    //    - 배경 음악이 계속 깔려 VAD가 오발동한 경우: 가장자리(marginFloor)와 중간(activeRms)이 비슷해 localCrest가 낮다.
    //    - 사용자가 크게 길게 말해 패딩 구간이 좁은 경우: 기존 학습된 this.noiseFloor의 2.5배를 상한으로 삼아 오차단 방지.
    const effectiveFloor = clamp(
      Math.max(this.noiseFloor, Math.min(localFloor, this.noiseFloor * 2.5)),
      o.minNoiseFloor,
      o.maxNoiseFloor,
    )

    // 배경 소음 바닥 갱신 (이번 구간의 하위 에너지가 합리적 범위일 때 서서히 반영)
    const candidateFloor = clamp(localFloor, o.minNoiseFloor, o.maxNoiseFloor)
    this.noiseFloor = clamp(
      this.noiseFloor * (1 - o.floorAlpha) + candidateFloor * o.floorAlpha,
      o.minNoiseFloor,
      o.maxNoiseFloor,
    )

    const snrRatio = activeRms / Math.max(effectiveFloor, o.minNoiseFloor)
    const localCrest = activeRms / Math.max(marginFloor, o.minNoiseFloor)

    // 활성 음성으로 인정할 윈도우 임계값
    const voiceWinThreshold = Math.max(o.minSpeechRms * 0.85, effectiveFloor * (o.snrMargin * 0.85))
    const activeWindows = winRms.filter(r => r >= voiceWinThreshold).length
    const activeMs = activeWindows * o.windowMs

    const metrics = {
      durationMs,
      activeRms: +activeRms.toFixed(4),
      peakRms: +peakRms.toFixed(4),
      marginFloor: +marginFloor.toFixed(4),
      noiseFloor: +this.noiseFloor.toFixed(4),
      snrRatio: +snrRatio.toFixed(2),
      localCrest: +localCrest.toFixed(2),
      activeMs,
    }

    // 판정 1: 짧은 충격음(박수, 식기 달그락, 기침 등 — 순간 피크는 높으나 지속시간이 minActiveMs 미만)
    if (peakRms >= o.minSpeechRms && activeMs > 0 && activeMs < o.minActiveMs) {
      return { pass: false, reason: 'impulse_noise', metrics }
    }

    // 판정 2: 절대 음량 미달 (무음 · 원거리 주변 대화 · 작은 웅얼거림)
    if (activeRms < o.minSpeechRms) {
      return { pass: false, reason: 'low_rms', metrics }
    }

    // 판정 3: 배경 소음 대비 신호비(SNR) 미달 또는 일정한 크기의 배경 음악/소음(localCrest 미달)
    // 단, 근접 대성 발화(activeRms >= minSpeechRms * 3.5)인데 패딩까지 말이 꽉 찬 경우는 통과 허용
    const isLoudFullClip = activeRms >= o.minSpeechRms * 3.5 && snrRatio >= o.snrMargin
    if (snrRatio < o.snrMargin || (!isLoudFullClip && localCrest < o.snrMargin * 0.85)) {
      return { pass: false, reason: 'low_snr', metrics }
    }

    // 판정 4: 활성 음성 지속 시간 미달
    if (activeMs < o.minActiveMs) {
      return { pass: false, reason: 'impulse_noise', metrics }
    }

    return { pass: true, reason: 'ok', metrics }
  }
}

let _agcGuardInstalled = false

/**
 * @ricky0123/vad-web 의 MicVAD가 내부적으로 autoGainControl: true 를 강제하는 문제를 막기 위해
 * getUserMedia의 오디오 제약 조건에서 autoGainControl을 기본 false로 고정한다.
 * (조용한 구간에 마이크 게인이 증폭되어 멀리 있는 대화나 매장 음악이 크게 들어오는 현상 방지)
 */
export function installMicAgcGuard() {
  if (_agcGuardInstalled) return
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) return
  _agcGuardInstalled = true

  const origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
  navigator.mediaDevices.getUserMedia = async function patchedGetUserMedia(constraints) {
    const allowAgc = Boolean(loadGateOverrides().autoGainControl)
    if (constraints && constraints.audio) {
      const audioObj = typeof constraints.audio === 'object' ? { ...constraints.audio } : {}
      audioObj.autoGainControl = allowAgc
      if (audioObj.echoCancellation === undefined) audioObj.echoCancellation = true
      if (audioObj.noiseSuppression === undefined) audioObj.noiseSuppression = true
      constraints = { ...constraints, audio: audioObj }
    }
    const stream = await origGetUserMedia(constraints)
    try {
      for (const track of stream.getAudioTracks()) {
        track.applyConstraints?.({
          autoGainControl: allowAgc,
          echoCancellation: true,
          noiseSuppression: true,
        }).catch(() => {})
      }
    } catch {}
    return stream
  }
}

/** 브라우저 localStorage / window 전역 객체에서 현장 튜닝 오버라이드 값을 읽는다. */
export function loadGateOverrides() {
  if (typeof window === 'undefined') return {}
  try {
    const raw = window.localStorage?.getItem('sttGateConfig')
    const fromStorage = raw ? JSON.parse(raw) : {}
    return { ...fromStorage, ...(window.__sttGateConfig || {}) }
  } catch {
    return window.__sttGateConfig || {}
  }
}
