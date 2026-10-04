// TTS 재생 중 끼어들기(barge-in) — 실험 기능. 기본 OFF. 켜고 끄는 곳은 아래 BARGE_IN_ENABLED 상수 하나다.
//
// 지금까지의 방식(반이중): TTS가 나오는 동안 마이크 감지(VAD)를 멈춘다. 에코를 사용자 말로 오인하지 않지만 손님이 말을 끊을 수 없다.
// 이 기능이 켜지면 VAD를 멈추지 않고, 재생 중인 소리의 크기(출력 레벨)를 분석해 "그 소리가 마이크로 되돌아온 만큼"을 무시한 뒤
// 그보다 확실히 큰 소리가 계속 들어올 때만 사용자 말로 보고 TTS를 끊는다.
//   - 브라우저 에코 제거(AEC)가 먼저 일부 지워 준다(마이크 스트림에 echoCancellation:true).
//   - 남은 에코는 BargeDetector가 "출력 레벨 × 결합 계수(스피커→마이크)"로 예상해서 빼고 판정한다.
// 한계: 파형 단위 상쇄가 아니라 소리 크기(엔벨로프) 기준이다. 스피커 음량·마이크 위치·실내 반향에 따라 임계값 조정이 필요할 수 있다.

// ★ 끼어들기 ON/OFF — 여기서 바꾼다(true = 켬, false = 끔). 바꾸면 저장 후 새로고침.
//   false(기본): 기존 방식 — TTS가 나오는 동안 마이크 감지를 멈춘다(손님이 말을 끊을 수 없다).
//   true: TTS 재생 중에도 마이크를 듣고, 사용자 말이 확인되면 TTS를 끊는다(실험).
export const BARGE_IN_ENABLED = false

export const isBargeInEnabled = () => BARGE_IN_ENABLED
/** React 컴포넌트에서 쓰는 형태(값이 코드 상수라 구독이 필요 없다). */
export const useBargeInEnabled = () => BARGE_IN_ENABLED

// ── 판정기 (순수 로직 — 오디오 장치 없이 시뮬레이션으로 검증한다) ──────────────────────
export const DEFAULTS = {
  frameMs: 50,        // 판정 주기
  outAudible: 0.01,   // 이 이상이면 TTS가 소리를 내는 중(RMS 0~1)
  absMin: 0.03,       // 마이크 레벨의 절대 하한 — 이보다 작은 소리는 사용자 말로 보지 않는다
  margin: 2.0,        // 예상 에코의 몇 배를 넘어야 사용자 말로 보는가
  floorMult: 3,       // 배경 소음 바닥의 몇 배를 넘어야 하는가
  sustainMs: 250,     // 이 시간 이상 계속 넘어야 인정(순간 잡음 배제)
  learnFrames: 14,    // 결합 계수를 추정할 최소 프레임(700ms). 마이크가 스피커 소리보다 늦게 들려서 재생 초반의 비율은 실제보다 작게 나온다
  forgetMs: 5000,     // 이만큼 조용했으면 결합 계수를 잊고 다시 학습한다(스피커 음량·위치가 바뀌었을 수 있다)
  envFrames: 8,       // 출력 레벨의 최근 N프레임(400ms) 최댓값을 쓴다 — 마이크가 스피커 소리보다 늦게 들리는 지연(최대 약 350ms) 보정
  ratioWindow: 60,    // 결합 계수 추정에 쓰는 프레임 수(3초)
}

export class BargeDetector {
  constructor(opts = {}) {
    this.o = { ...DEFAULTS, ...opts }
    this.floor = 0.01   // 배경 소음 바닥(TTS가 없을 때의 마이크 레벨)
    this._resetPlayback()
  }

  _resetPlayback() {
    this.ratios = []    // 최근 마이크/출력 비율 — 스피커→마이크 결합은 장치의 성질이라 문장 사이 짧은 정적에서는 지우지 않는다
    this.outs = []      // 최근 출력 레벨
    this.sustain = 0
    this.quietMs = 0    // 재생 소리가 없었던 시간
  }

  /** 한 프레임(frameMs)마다 호출. mic/out은 RMS(0~1). 끼어들기로 판정되면 true. */
  feed(mic, out) {
    const o = this.o
    if (out < o.outAudible) {
      // 재생 소리가 없다(문장 사이·끝) → 배경 소음 바닥만 서서히 갱신한다. 결합 계수는 오래 조용했을 때만 잊는다.
      this.floor = this.floor * 0.95 + mic * 0.05
      this.sustain = 0
      this.outs.length = 0
      this.quietMs += o.frameMs
      if (this.quietMs > o.forgetMs) this.ratios.length = 0
      return false
    }
    this.quietMs = 0
    this.outs.push(out); if (this.outs.length > o.envFrames) this.outs.shift()
    const outEnv = Math.max(...this.outs)
    this.ratios.push(mic / outEnv); if (this.ratios.length > o.ratioWindow) this.ratios.shift()
    if (this.ratios.length < o.learnFrames) return false   // 아직 결합 계수를 모른다

    // 결합 계수 k: 비율의 70% 지점. TTS 소리는 단어마다 크기가 변하고 마이크 쪽 에코는 지연돼서 비율이 넓게 퍼진다 — 낮은 쪽을 쓰면
    // 에코를 과소평가해 오발동한다. 사용자가 말해도 판정은 250ms 안에 끝나므로 높은 쪽 비율이 오염되기 전에 결과가 난다.
    const sorted = [...this.ratios].sort((a, b) => a - b)
    const k = sorted[Math.floor(sorted.length * 0.7)]
    const threshold = Math.max(o.absMin, this.floor * o.floorMult, o.margin * k * outEnv)
    this.sustain = mic > threshold ? this.sustain + o.frameMs : Math.max(0, this.sustain - o.frameMs)
    return this.sustain >= o.sustainMs
  }

  reset() { this._resetPlayback() }
}

// ── 오디오 탭: 재생 소리와 마이크의 레벨 측정 ───────────────────────────────────────
let _ctx = null
let _outAnalyser = null
let _micAnalyser = null
let _micStream = null
const _buf = { out: null, mic: null }

function ensureCtx() {
  if (!_ctx) {
    _ctx = new (window.AudioContext || window.webkitAudioContext)()
    _outAnalyser = _ctx.createAnalyser(); _outAnalyser.fftSize = 1024
    _outAnalyser.connect(_ctx.destination)
    _buf.out = new Float32Array(_outAnalyser.fftSize)
  }
  return _ctx
}

const rms = (analyser, buf) => {
  analyser.getFloatTimeDomainData(buf)
  let s = 0
  for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i]
  return Math.sqrt(s / buf.length)
}

/**
 * 재생할 <audio>를 출력 분석기에 연결한다(재생 시작 전에 호출). 꺼져 있거나 AudioContext를 쓸 수 없으면 아무것도 하지 않는다 —
 * 이 경우 소리는 평소처럼 <audio>로 나간다. (AudioContext가 멈춰 있으면 연결하지 않는다: 연결하면 소리가 안 나올 수 있다.)
 */
export function tapOutput(audio) {
  if (!isBargeInEnabled() || !audio) return
  try {
    const ctx = ensureCtx()
    if (ctx.state === 'suspended') { ctx.resume().catch(() => {}); return }   // 아직 못 쓰면 이번 재생은 건너뛴다
    if (ctx.state !== 'running') return
    ctx.createMediaElementSource(audio).connect(_outAnalyser)
  } catch { /* 이미 연결된 요소 등 — 무시 */ }
}

export const outputLevel = () => (_outAnalyser ? rms(_outAnalyser, _buf.out) : 0)
export const micLevel = () => (_micAnalyser ? rms(_micAnalyser, _buf.mic) : 0)

async function startMic() {
  if (_micAnalyser) return
  const ctx = ensureCtx()
  if (ctx.state === 'suspended') await ctx.resume().catch(() => {})
  // AEC·잡음 억제는 켜고 자동 이득(AGC)은 끈다 — AGC가 켜져 있으면 에코가 작을 때 마이크 감도를 올려 레벨 비교가 흐려진다.
  _micStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: false } })
  const src = ctx.createMediaStreamSource(_micStream)
  _micAnalyser = ctx.createAnalyser(); _micAnalyser.fftSize = 1024
  _buf.mic = new Float32Array(_micAnalyser.fftSize)
  src.connect(_micAnalyser)   // destination에는 연결하지 않는다(마이크 소리를 스피커로 내보내지 않음)
}

function stopMic() {
  try { _micStream?.getTracks().forEach(t => t.stop()) } catch {}
  _micStream = null; _micAnalyser = null
}

/**
 * 끼어들기 감시를 시작한다. 마이크 레벨과 출력 레벨을 BargeDetector에 계속 넣어 사용자가 말을 시작하면 onBarge를 부른다.
 * canFire(선택): false를 돌려주면 판정이 나도 아직 부르지 않는다(이중 확인용 — 예: VAD도 말소리를 감지했을 때만).
 * 반환값: 중지 함수. 마이크를 열지 못하면 아무것도 하지 않고 중지 함수만 돌려준다(끼어들기는 동작하지 않는다).
 * debug: window.__bargeInDebug에 최근 값을 남긴다(콘솔에서 확인: 마이크/출력 레벨과 판정 임계값 조정용).
 */
export function startBargeWatch({ onBarge, canFire, options } = {}) {
  const det = new BargeDetector(options)
  let timer = null, stopped = false, cooldownUntil = 0
  startMic().then(() => {
    if (stopped) { stopMic(); return }
    timer = setInterval(() => {
      const mic = micLevel(), out = outputLevel()
      const hit = det.feed(mic, out)
      window.__bargeInDebug = { mic: +mic.toFixed(4), out: +out.toFixed(4), floor: +det.floor.toFixed(4), sustain: det.sustain, learned: det.ratios.length }
      if (hit && performance.now() > cooldownUntil && (!canFire || canFire())) {
        cooldownUntil = performance.now() + 1500   // 한 번 끊은 뒤에는 잠시 다시 판정하지 않는다
        det.reset()
        onBarge?.()
      }
    }, det.o.frameMs)
  }).catch(e => console.warn('[bargeIn] 마이크를 열지 못해 끼어들기를 쓸 수 없다:', e?.message ?? e))
  return () => { stopped = true; clearInterval(timer); stopMic() }
}
