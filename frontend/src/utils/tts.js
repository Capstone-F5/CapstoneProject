import { getCachedAudio } from './ttsCache.js'
import { tapOutput } from './bargeIn.js'

let _current = null
// 재생 요청 일련번호. playTTS는 await 지점이 여러 개라, 앞선 요청이 대기하는 사이
// 다음 요청이 시작될 수 있다(StrictMode 이중 마운트 등). 그때 stopTTS()는 아직
// _current가 비어 있어 아무것도 못 멈추고 결국 두 소리가 겹친다.
// 각 await 뒤에 이 번호를 확인해 뒤처진 요청을 버린다.
let _seq = 0

// 재생 시작·끝을 알린다 — 채팅(음성) 모드의 마이크가 스피커 소리를 되받지 않도록 ChatPanel이 듣는다.
const emit = (name) => { try { window.dispatchEvent(new Event(name)) } catch {} }
const trackEnd = (audio) => {
  const done = () => emit('kiosk-tts-end')
  audio.addEventListener('ended', done, { once: true })
  audio.addEventListener('error', done, { once: true })
  audio.addEventListener('pause', done, { once: true })
}

export function stopTTS() {
  _seq++
  if (_current) { _current.pause(); _current.currentTime = 0; _current = null }
}

// opts.cache=false면 사전 녹음 캐시를 건너뛰고 항상 API로 합성한다(캐시와 API 소리를 비교하는 테스트용).
export async function playTTS(text, { cache = true } = {}) {
  stopTTS()
  const seq = _seq

  try {
    const cached = cache ? await getCachedAudio(text) : null
    if (seq !== _seq) return
    if (cached) {
      _current = cached
      tapOutput(cached)   // 끼어들기 ON이면 재생 소리 크기를 분석기에 연결(꺼져 있으면 아무것도 안 함)
      emit('kiosk-tts-start')
      trackEnd(cached)
      // 재생 실패를 catch로 떨어뜨려 API 경로로 넘긴다. 예전엔 로그만 찍고
      // return 해버려서, 사전 녹음 파일이 없으면 fallback 없이 무음이 됐다.
      await cached.play()
      return
    }
  } catch (e) {
    if (seq !== _seq) return
    console.warn('[TTS] 캐시 재생 실패 — API로 전환:', e?.name ?? e)
  }

  try {
    const res = await fetch('/ai_modules/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, format: 'mp3', language: 'ko' }),
    })
    if (seq !== _seq) return
    if (!res.ok) {
      console.warn('[TTS] API 응답 오류:', res.status, text)
      return
    }
    const blob = await res.blob()
    if (seq !== _seq) return
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    _current = audio
    tapOutput(audio)
    emit('kiosk-tts-start')
    trackEnd(audio)
    audio.onended = () => { URL.revokeObjectURL(url); if (_current === audio) _current = null }
    audio.play().catch(e => { console.warn('[TTS] API 재생 차단:', e?.name ?? e); emit('kiosk-tts-end') })
  } catch (e) {
    console.warn('[TTS] API 요청 실패:', e)
  }
}
