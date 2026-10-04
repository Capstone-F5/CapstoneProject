// 주문번호 낭독 — 미리 녹음한 조각(public/audio/numbers/, scripts/generateCommonAudio.js가 만든다)을 이어 붙여 읽는다.
// "주문번호는" + [백] + [십] + [일의 자리] + "번입니다"로 1~999번을 모두 조합하므로 번호마다 API로 합성할 필요가 없다.
// 조각이 없거나 재생이 안 되면 문장 전체를 playTTS(API)로 읽는다(이때는 한글 수사로 적는다).
import { playTTS, stopTTS } from './tts.js'

const BASE = '/audio/numbers/'
const TRIM_THRESHOLD = 0.015   // 이 크기 아래로 시작·끝나는 구간은 무음으로 보고 자른다(TTS 조각 앞뒤 여백 제거)
const GAP_AFTER_PREFIX = 0.1   // "주문번호는" 뒤에 숫자 앞의 짧은 쉼(초)
const GAP_BETWEEN = 0.02       // 숫자 조각 사이

/** 1~999 → 재생할 조각 이름 순서. 범위 밖이면 null. 예) 12 → [prefix, ten, n2, suffix], 123 → [prefix, hundred, n2, ten, n3, suffix] */
export function numberClips(n) {
  if (!Number.isInteger(n) || n < 1 || n > 999) return null
  const h = Math.floor(n / 100), t = Math.floor(n / 10) % 10, o = n % 10
  const out = ['prefix']
  if (h) { if (h > 1) out.push(`n${h}`); out.push('hundred') }   // 100은 "일백"이 아니라 "백"
  if (t) { if (t > 1) out.push(`n${t}`); out.push('ten') }       // 10은 "일십"이 아니라 "십"
  if (o) out.push(`n${o}`)
  out.push('suffix')
  return out
}

let _ctx = null
const _clips = new Map()   // 조각 이름 → { buf, start, dur } (앞뒤 무음을 뺀 재생 구간)
const emit = (name) => { try { window.dispatchEvent(new Event(name)) } catch {} }

function trimRange(buf) {
  const ch = buf.getChannelData(0)
  let s = 0, e = ch.length - 1
  while (s < e && Math.abs(ch[s]) < TRIM_THRESHOLD) s++
  while (e > s && Math.abs(ch[e]) < TRIM_THRESHOLD) e--
  const pad = Math.round(buf.sampleRate * 0.01)   // 자른 자리에서 소리가 뚝 끊기지 않게 10ms 여유
  s = Math.max(0, s - pad); e = Math.min(ch.length - 1, e + pad)
  return { buf, start: s / buf.sampleRate, dur: (e - s) / buf.sampleRate }
}

async function loadClip(name) {
  if (_clips.has(name)) return _clips.get(name)
  const res = await fetch(`${BASE}${name}.mp3`)
  // 파일이 없을 때 SPA가 index.html을 200으로 돌려주므로 content-type까지 본다(ttsCache.js와 같은 이유)
  if (!res.ok || !(res.headers.get('content-type') ?? '').startsWith('audio/')) throw new Error(`조각 없음: ${name}`)
  const buf = await _ctx.decodeAudioData(await res.arrayBuffer())
  const clip = trimRange(buf)
  _clips.set(name, clip)
  return clip
}

/** 숫자를 한글 한자어 수사로 쓴다(12 → "십이"). 대체 경로의 TTS 문장에 쓴다 — "12번"이라고 적으면 TTS가 "열두 번"이라고 읽는다. */
export function koreanNumber(n) {
  const D = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
  const h = Math.floor(n / 100), t = Math.floor(n / 10) % 10, o = n % 10
  return (h ? (h > 1 ? D[h] : '') + '백' : '') + (t ? (t > 1 ? D[t] : '') + '십' : '') + D[o]
}

/** 주문번호를 읽는다. 미리 녹음한 숫자 조각을 이어 붙인다. 재생이 끝나면 resolve.
 *  재생 중에는 kiosk-tts-start/end를 보내 음성 채팅의 마이크가 이 소리를 듣지 않게 한다. */
export async function speakOrderNumber(n) {
  const fallback = () => playTTS(Number.isInteger(n) && n >= 1 && n <= 999 ? `주문번호는 ${koreanNumber(n)} 번입니다` : `주문번호는 ${n}번입니다`)
  const names = numberClips(n)
  if (!names) return fallback()

  let started = false
  try {
    _ctx = _ctx ?? new (window.AudioContext || window.webkitAudioContext)()
    const clips = await Promise.all(names.map(loadClip))
    if (_ctx.state === 'suspended') await _ctx.resume()
    stopTTS()   // 다른 안내음이 재생 중이면 끊는다
    started = true
    emit('kiosk-tts-start')
    let at = _ctx.currentTime + 0.05
    let last = null
    clips.forEach((c, i) => {
      const src = _ctx.createBufferSource()
      src.buffer = c.buf
      src.connect(_ctx.destination)
      src.start(at, c.start, c.dur)
      at += c.dur + (i === 0 ? GAP_AFTER_PREFIX : GAP_BETWEEN)
      last = src
    })
    await new Promise(resolve => { last.onended = resolve })
    emit('kiosk-tts-end')
  } catch (e) {
    console.warn('[numberSpeech] 조각 재생 실패 — 문장 전체를 API로 읽는다:', e?.message ?? e)
    if (started) emit('kiosk-tts-end')
    await fallback()
  }
}
