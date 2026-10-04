// BargeDetector 시뮬레이션 — 오디오 장치 없이 레벨 시퀀스로 판정을 검증한다. 실행: node scripts/testBargeDetector.mjs
import { BargeDetector } from '../src/utils/bargeIn.js'

let seed = 42
const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296 }
const noise = (a) => a * (rnd() - 0.5) * 2
// TTS 소리의 크기 변화: 단어 단위로 오르내리는 엔벨로프(0.05~0.4)
const ttsEnv = (i) => 0.05 + 0.35 * Math.abs(Math.sin(i * 0.37)) * (0.6 + 0.4 * Math.abs(Math.sin(i * 0.11)))

/** 시나리오를 돌려 최초 발동 프레임(없으면 null)을 돌려준다. echoK: 스피커→마이크 결합 계수, lag: 마이크가 스피커 소리보다 늦게 들리는 프레임 수 */
function run({ frames = 120, echoK = 0.25, userFrom = null, userLevel = 0.15, lag = 2, ttsFrom = 0, ttsTo = frames, floorNoise = 0.004, det = new BargeDetector() }) {
  const out = (i) => (i >= ttsFrom && i < ttsTo ? ttsEnv(i) : 0)
  for (let i = 0; i < frames; i++) {
    const o = out(i)
    const echo = echoK * out(Math.max(0, i - lag))
    const user = userFrom != null && i >= userFrom ? userLevel * (0.8 + 0.4 * rnd()) : 0
    const mic = Math.max(0, echo + user + Math.abs(noise(floorNoise)))
    if (det.feed(mic, o)) return i
  }
  return null
}

const cases = []
const check = (name, got, expect) => { const ok = expect(got); cases.push(ok); console.log(`${ok ? '✓' : '✗'} ${name}: ${got === null ? '발동 안 함' : `${got}프레임(${got * 50}ms)에 발동`}`) }

console.log('--- 발동하면 안 되는 경우 (에코만) ---')
for (const k of [0.05, 0.15, 0.25, 0.4, 0.6]) check(`에코만, 결합 계수 ${k}`, run({ echoK: k }), g => g === null)
check('에코만 + 지연 6프레임(300ms)', run({ echoK: 0.3, lag: 6 }), g => g === null)
check('에코만 + 배경 소음 0.02', run({ echoK: 0.25, floorNoise: 0.02 }), g => g === null)
check('조용한 마이크 + TTS 재생 중', run({ echoK: 0 }), g => g === null)
check('TTS 없이 사용자만(VAD가 처리, 판정기는 무시)', run({ ttsFrom: 999, userFrom: 20 }), g => g === null)

console.log('--- 발동해야 하는 경우 (에코 + 사용자 말) ---')
for (const [k, u] of [[0.05, 0.12], [0.15, 0.15], [0.25, 0.2], [0.4, 0.3]]) {
  const g = run({ echoK: k, userFrom: 40, userLevel: u })
  check(`결합 계수 ${k}, 사용자 말 ${u}`, g, v => v !== null && v >= 40 && v <= 40 + 10)   // 말 시작 후 500ms 안
}
check('조용한 에코(0)에서 사용자 말 0.08', run({ echoK: 0, userFrom: 40, userLevel: 0.08 }), v => v !== null && v <= 50)

console.log('--- 경계 ---')
check('TTS 시작 직후(결합 계수 학습 700ms 안) 말해도 바로는 발동 안 함', run({ echoK: 0.25, userFrom: 0, userLevel: 0.2 }), g => g === null || g * 50 >= 700)
check('너무 약한 말(0.02)은 무시(절대 하한)', run({ echoK: 0.1, userFrom: 40, userLevel: 0.02 }), g => g === null)
check('짧은 잡음(100ms) 하나는 무시', (() => { const d = new BargeDetector(); let hit = null; for (let i = 0; i < 100; i++) { const o = ttsEnv(i), m = 0.25 * o + (i >= 40 && i < 42 ? 0.4 : 0.003); if (d.feed(m, o)) { hit = i; break } } return hit })(), g => g === null)

console.log('--- 재생 사이 정적 뒤 다시 시작 ---')
{
  const d = new BargeDetector(); let hit = null
  for (let i = 0; i < 200; i++) {
    const playing = (i < 60) || (i >= 90)            // 60~90프레임(1.5초)은 문장 사이 정적
    const o = playing ? ttsEnv(i) : 0
    const m = 0.25 * o + 0.004
    if (d.feed(m, o)) { hit = i; break }
  }
  check('정적 후 재시작한 TTS의 에코만', hit, g => g === null)
}

console.log('--- 문장 사이 정적 뒤 사용자가 말하는 경우 (결합 계수 유지) ---')
{
  const d = new BargeDetector(); let hit = null
  for (let i = 0; i < 220; i++) {
    const playing = (i < 60) || (i >= 75)            // 60~75프레임(0.75초)은 문장 사이 정적
    const o = playing ? ttsEnv(i) : 0
    const user = i >= 110 ? 0.18 : 0                 // 두 번째 문장 도중에 사용자가 끼어듦
    const m = 0.25 * o + user + 0.004
    if (d.feed(m, o) && hit === null) hit = i
  }
  check('두 번째 문장 도중 사용자 끼어들기 (정적 뒤에도 바로 판정)', hit, g => g !== null && g >= 110 && g <= 116)
}

console.log(`\n${cases.filter(Boolean).length}/${cases.length} 통과`)
process.exit(cases.every(Boolean) ? 0 : 1)
