import { getCachedAudio } from './ttsCache.js'

let _current = null

export function stopTTS() {
  if (_current) { _current.pause(); _current.currentTime = 0; _current = null }
}

export async function playTTS(text) {
  stopTTS()
  try {
    const cached = await getCachedAudio(text)
    if (cached) {
      _current = cached
      cached.play().catch(e => console.warn('[TTS] cached autoplay blocked:', e))
      return
    }
  } catch (e) {
    console.warn('[TTS] cache lookup failed:', e)
  }
  try {
    const res = await fetch('/ai_modules/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, format: 'mp3', language: 'ko' }),
    })
    if (!res.ok) {
      console.warn('[TTS] API 응답 오류:', res.status, text)
      return
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    _current = audio
    audio.onended = () => { URL.revokeObjectURL(url); if (_current === audio) _current = null }
    audio.play().catch(e => console.warn('[TTS] API autoplay blocked:', e))
  } catch (e) {
    console.warn('[TTS] API 요청 실패:', e)
  }
}
