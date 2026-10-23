// AudioEnergyGate 시뮬레이션 검증 — 실제 오디오 파형(16kHz Float32Array)을 합성해
// 근접 발화는 통과하고 원거리 대화·배경 음악·충격음은 차단되는지 검증한다.
// 실행: node frontend/scripts/testAudioGate.mjs
import { AudioEnergyGate } from '../src/utils/audioGate.js'

const SR = 16000
let seed = 12345
const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296 }
// 3개 균등분포 합의 분산 = 3*(1/12) = 1/4 (표준편차 0.5) → 2를 곱하면 표준편차(RMS) = 1.0
const randn = () => (rnd() + rnd() + rnd() - 1.5) * 2.0

/**
 * 16kHz Float32Array 파형 생성기
 * @param {object} opts
 * @param {number} opts.durationMs 전체 클립 길이 (선행/후행 패딩 포함)
 * @param {number} opts.bgRms 배경 소음/음악 기본 RMS
 * @param {number} opts.bgMod 배경 음악처럼 주기적으로 흔들리는 진폭 비율(0~1)
 * @param {number} opts.speechStartMs 발화 시작 시각(ms)
 * @param {number} opts.speechEndMs 발화 종료 시각(ms)
 * @param {number} opts.speechRms 발화 음절 목표 RMS
 */
function synthClip({
  durationMs = 2000,
  bgRms = 0.004,
  bgMod = 0.0,
  speechStartMs = 600,
  speechEndMs = 1400,
  speechRms = 0.0,
} = {}) {
  const n = Math.floor((SR * durationMs) / 1000)
  const buf = new Float32Array(n)
  const s0 = Math.floor((SR * speechStartMs) / 1000)
  const s1 = Math.floor((SR * speechEndMs) / 1000)

  // 0.8*sin(w1) + 0.6*sin(w2) 의 평균 제곱 = 0.5*(0.64 + 0.36) = 0.5 → sqrt(2)를 곱하면 RMS = 1.0
  for (let i = 0; i < n; i++) {
    const t = i / SR
    const mod = 1 + bgMod * Math.sin(2 * Math.PI * 2.3 * t) * Math.cos(2 * Math.PI * 0.7 * t)
    let sample = randn() * bgRms * mod

    if (speechRms > 0 && i >= s0 && i < s1) {
      const sylEnv = 0.8 + 0.35 * Math.sin(2 * Math.PI * 4.5 * (t - speechStartMs / 1000))
      const voiced = (0.8 * Math.sin(2 * Math.PI * 180 * t) + 0.6 * Math.sin(2 * Math.PI * 540 * t)) * Math.SQRT2
      sample += voiced * speechRms * sylEnv
    }
    buf[i] = Math.max(-1, Math.min(1, sample))
  }
  return buf
}

const results = []
function check(name, res, expectPass, expectReason = null) {
  const ok = res.pass === expectPass && (expectReason === null || res.reason === expectReason)
  results.push(ok)
  const status = ok ? '✓' : '✗'
  console.log(
    `${status} ${name} → pass=${res.pass} (${res.reason}) ` +
    `[activeRms=${res.metrics.activeRms}, marginFloor=${res.metrics.marginFloor}, snr=${res.metrics.snrRatio}, crest=${res.metrics.localCrest}, activeMs=${res.metrics.activeMs}]`
  )
}

console.log('=== 1. 통과해야 하는 경우 (키오스크 정면 고객 정상 발화) ===')
{
  const gate = new AudioEnergyGate()
  check(
    '조용한 매장 + 일반 주문 발화 ("치즈버거 단품 하나 주세요", RMS 0.06)',
    gate.evaluate(synthClip({ durationMs: 2400, bgRms: 0.004, speechStartMs: 500, speechEndMs: 1800, speechRms: 0.06 })),
    true, 'ok'
  )
  check(
    '조용한 매장 + 짧은 대답 ("네", 210ms 발화, RMS 0.045)',
    gate.evaluate(synthClip({ durationMs: 1500, bgRms: 0.004, speechStartMs: 550, speechEndMs: 760, speechRms: 0.045 })),
    true, 'ok'
  )
  check(
    '조용한 매장 + 조심스러운 목소리 ("포장이요", RMS 0.025)',
    gate.evaluate(synthClip({ durationMs: 1800, bgRms: 0.004, speechStartMs: 500, speechEndMs: 1100, speechRms: 0.025 })),
    true, 'ok'
  )
  check(
    '배경 음악(RMS 0.015)이 흐르는 매장 + 정면 고객 발화 (RMS 0.065)',
    gate.evaluate(synthClip({ durationMs: 2200, bgRms: 0.015, bgMod: 0.2, speechStartMs: 550, speechEndMs: 1650, speechRms: 0.065 })),
    true, 'ok'
  )
  check(
    '시끄러운 매장 소음(RMS 0.022) + 정면 고객 또렷한 발화 (RMS 0.08)',
    gate.evaluate(synthClip({ durationMs: 2200, bgRms: 0.022, bgMod: 0.15, speechStartMs: 500, speechEndMs: 1700, speechRms: 0.08 })),
    true, 'ok'
  )
}

console.log('\n=== 2. 차단되어야 하는 경우 (배경 소음 · 매장 음악 · 주변 대화 · 충격음) ===')
{
  const gate = new AudioEnergyGate()
  check(
    '무음/정적 구간 오발동 (RMS 0.003)',
    gate.evaluate(synthClip({ durationMs: 1600, bgRms: 0.003, speechRms: 0 })),
    false, 'low_rms'
  )
  check(
    '원거리(2~3m 밖) 주변 테이블 대화 (AGC OFF, RMS 0.011)',
    gate.evaluate(synthClip({ durationMs: 2000, bgRms: 0.003, speechStartMs: 500, speechEndMs: 1500, speechRms: 0.011 })),
    false, 'low_rms'
  )
  check(
    '원거리(1.8m 밖) 지나가는 행인 짧은 말소리 (RMS 0.014)',
    gate.evaluate(synthClip({ durationMs: 1800, bgRms: 0.004, speechStartMs: 600, speechEndMs: 1200, speechRms: 0.014 })),
    false, 'low_rms'
  )
  check(
    '매장 배경 음악(BGM 보컬) 지속 재생으로 VAD가 오발동한 경우 (평균 RMS 0.03, 진폭 변동 30%)',
    gate.evaluate(synthClip({ durationMs: 3000, bgRms: 0.03, bgMod: 0.3, speechRms: 0 })),
    false, 'low_snr'
  )
  check(
    '매장 내 웅성거림(Babble Noise, RMS 0.025) 위에 멀리서 들리는 대화(RMS 0.015)',
    gate.evaluate(synthClip({ durationMs: 2500, bgRms: 0.025, bgMod: 0.2, speechStartMs: 700, speechEndMs: 1700, speechRms: 0.015 })),
    false, 'low_snr'
  )
  check(
    '식기 부딪히는 소리 / 박수 / 기침 등 짧은 충격음 (60ms 피크, RMS 0.12)',
    gate.evaluate(synthClip({ durationMs: 1500, bgRms: 0.004, speechStartMs: 600, speechEndMs: 660, speechRms: 0.12 })),
    false, 'impulse_noise'
  )
  check(
    '너무 짧은 오디오 조각 (100ms)',
    gate.evaluate(synthClip({ durationMs: 100, bgRms: 0.004, speechStartMs: 0, speechEndMs: 100, speechRms: 0.08 })),
    false, 'too_short'
  )
  check(
    '배경 음악으로 인해 끊기지 않고 20초간 녹음된 비정상 클립',
    gate.evaluate(synthClip({ durationMs: 20000, bgRms: 0.025, speechStartMs: 500, speechEndMs: 19000, speechRms: 0.06 })),
    false, 'too_long'
  )
}

const passed = results.filter(Boolean).length
console.log(`\n결과: ${passed}/${results.length} 테스트 통과`)
process.exit(passed === results.length ? 0 : 1)
