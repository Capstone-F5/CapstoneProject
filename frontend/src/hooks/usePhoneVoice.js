import { useCallback, useEffect, useRef, useState } from 'react'
import { stopTTS } from '../utils/tts'

// 마이크 버튼을 한 번 누르면 전화번호 한 번만 듣는다(상시 VAD와 별개).
// 말이 시작된 뒤 SILENCE_MS 동안 조용하면 끝, 말이 없으면 NO_SPEECH_MS 뒤 취소, 어떤 경우든 MAX_MS를 넘기지 않는다.
const SILENCE_MS   = 1600
const NO_SPEECH_MS = 6000
const MAX_MS       = 14000
const RMS_ON       = 0.02   // 이 크기 이상이면 말하는 중으로 본다(0~1)
const MIN_BYTES    = 1500   // 이보다 작은 녹음은 말이 없는 것으로 보고 서버에 보내지 않는다

/**
 * @param {{ language?: string, onDigits: (digits: string, complete: boolean) => void, onError?: (msg: string) => void }} opts
 * @returns {{ state: 'idle'|'listening'|'processing', start: () => void, cancel: () => void }}
 */
export default function usePhoneVoice({ language = 'ko', onDigits, onError }) {
  const [state, setState] = useState('idle')
  const stateRef = useRef('idle')
  const cleanupRef = useRef(null)
  const cbRef = useRef({ onDigits, onError })
  cbRef.current = { onDigits, onError }

  const set = (s) => { stateRef.current = s; setState(s) }

  const cancel = useCallback(() => {
    cleanupRef.current?.()
    cleanupRef.current = null
    set('idle')
  }, [])

  // 화면이 바뀌어 언마운트되면 마이크를 반드시 놓는다
  useEffect(() => () => { cleanupRef.current?.() }, [])

  const start = useCallback(async () => {
    if (stateRef.current !== 'idle') return
    stopTTS()   // 안내 음성이 마이크로 들어가지 않게
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
    } catch (e) {
      cbRef.current.onError?.('mic')
      return
    }
    set('listening')

    const chunks = []
    const rec = new MediaRecorder(stream)
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 1024
    ctx.createMediaStreamSource(stream).connect(analyser)
    const buf = new Uint8Array(analyser.fftSize)

    let heardSpeech = false
    let lastVoiceAt = performance.now()
    const startedAt = lastVoiceAt
    let finished = false

    const release = () => {
      clearInterval(timer)
      stream.getTracks().forEach(t => t.stop())
      ctx.close().catch(() => {})
    }

    const finish = () => {
      if (finished) return
      finished = true
      if (rec.state !== 'inactive') rec.stop()   // onstop에서 업로드
    }

    rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
    rec.onstop = async () => {
      release()
      cleanupRef.current = null
      const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' })
      if (!heardSpeech || blob.size < MIN_BYTES) { set('idle'); cbRef.current.onError?.('nospeech'); return }
      set('processing')
      try {
        const form = new FormData()
        form.append('audio', blob, 'audio.webm')
        form.append('language', language)
        const res = await fetch('/ai_modules/stt/phone', { method: 'POST', body: form })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!data.digits) cbRef.current.onError?.('nodigits')
        else cbRef.current.onDigits(data.digits, !!data.complete)
      } catch {
        cbRef.current.onError?.('network')
      } finally {
        set('idle')
      }
    }

    const timer = setInterval(() => {
      analyser.getByteTimeDomainData(buf)
      let sum = 0
      for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v }
      const rms = Math.sqrt(sum / buf.length)
      const now = performance.now()
      if (rms > RMS_ON) { heardSpeech = true; lastVoiceAt = now }
      if (heardSpeech && now - lastVoiceAt > SILENCE_MS) finish()
      else if (!heardSpeech && now - startedAt > NO_SPEECH_MS) finish()
      else if (now - startedAt > MAX_MS) finish()
    }, 100)

    // 취소·언마운트: 녹음을 버리고(업로드 없이) 마이크를 놓는다
    cleanupRef.current = () => {
      finished = true
      rec.onstop = null
      if (rec.state !== 'inactive') rec.stop()
      release()
    }
    rec.start()
  }, [language])

  return { state, start, cancel }
}
