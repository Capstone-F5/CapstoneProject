import { useState, useEffect, useRef, useCallback } from 'react'
import { useMicVAD, utils } from '@ricky0123/vad-react'
import { useLocale } from '../i18n/LocaleContext'

const CSS = `
  @keyframes chatBlink { 0%,80%,100%{opacity:0.2} 40%{opacity:1} }
  .chat-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#555; margin:0 2px; animation:chatBlink 1.2s infinite }
  .chat-dot:nth-child(2){ animation-delay:.2s }
  .chat-dot:nth-child(3){ animation-delay:.4s }
  @keyframes waveBar { 0%,100%{height:4px} 50%{height:18px} }
  .wave-bar { display:inline-block; width:4px; border-radius:2px; background:#744032; animation:waveBar 0.75s ease-in-out infinite; min-height:4px }
  .wave-bar:nth-child(2){ animation-delay:.12s }
  .wave-bar:nth-child(3){ animation-delay:.24s }
  .wave-bar:nth-child(4){ animation-delay:.12s }
  .wave-bar:nth-child(5){ animation-delay:0s }
`

// 네이티브 지원 locale (ko/zh/ja 외 모든 언어 → 영어로 fallback)
const NATIVE_LOCALES = new Set(['ko', 'zh', 'ja'])
const langToLocale = (lang) => NATIVE_LOCALES.has(lang) ? lang : 'en'

const INIT_MESSAGES = [
  {
    id: 'init', role: 'bot',
    text: '안녕하세요! 저는 F BURGER 주문 도우미입니다 🍔\n메뉴 추천, 알레르기 정보, 주문 방법 등 궁금한 점을 말씀해 주세요.',
  },
]

function getSessionId() {
  const KEY = 'kiosk_llm_session_id'
  let sid = sessionStorage.getItem(KEY)
  if (!sid) {
    sid = crypto.randomUUID?.() ?? `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`
    sessionStorage.setItem(KEY, sid)
  }
  return sid
}

export default function ChatPanel({ onClose }) {
  const { setLocale } = useLocale()

  const [messages,  setMessages]  = useState(INIT_MESSAGES)
  const [isTyping,  setIsTyping]  = useState(false)
  const [listening, setListening] = useState(false)

  const scrollRef       = useRef(null)
  const activeRef       = useRef(true)
  const isTypingRef     = useRef(false)
  const sessionIdRef    = useRef(getSessionId())
  const audioRef        = useRef(null)    // 재생 중 Audio — 정리용
  // 첫 발화 감지 언어 — sessionStorage 연동으로 채팅 닫았다 열어도 유지
  // nav('start') 시 App에서 sessionStorage 항목 삭제 → 새 손님은 null로 시작
  const detectedLangRef = useRef(sessionStorage.getItem('kiosk_detected_lang') || null)

  // onSpeechEnd를 ref로 관리 → VAD 옵션이 재생성되지 않도록
  const speechEndHandlerRef = useRef(null)
  // async 함수 안에서 최신 vad 인스턴스에 접근하기 위한 ref
  const vadRef = useRef(null)

  useEffect(() => { isTypingRef.current = isTyping }, [isTyping])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, isTyping])

  // ─── Silero VAD ──────────────────────────────────────────────────────────────

  const vad = useMicVAD({
    // 모델 로딩 완료 후 자동 시작 — 로딩 전 start() 호출로 인한 흰 화면 방지
    startOnLoad: true,
    positiveSpeechThreshold: 0.8,
    negativeSpeechThreshold: 0.35,
    minSpeechFrames: 4,
    preSpeechPadFrames: 1,
    redemptionFrames: 10,
    workletURL: '/vad.worklet.bundle.min.js',
    modelURL: '/silero_vad.onnx',
    onSpeechStart: () => {
      if (activeRef.current && !isTypingRef.current) setListening(true)
    },
    onSpeechEnd: (audio) => speechEndHandlerRef.current?.(audio),
    onVADMisfire: () => setListening(false),
  })

  // vadRef 항상 최신 유지
  useEffect(() => { vadRef.current = vad }, [vad])

  // speechEndHandlerRef 업데이트 — isTyping·detectedLang 등 최신 상태 참조
  speechEndHandlerRef.current = useCallback(async (audio) => {
    setListening(false)
    if (!activeRef.current || isTypingRef.current) return

    // Float32Array(16 kHz) → WAV Blob → 백엔드 Whisper
    const wavBlob = new Blob([utils.encodeWAV(audio)], { type: 'audio/wav' })
    if (wavBlob.size < 2000) return   // 너무 짧으면 무시 (VAD misfire 보험)

    const form = new FormData()
    form.append('audio', wavBlob, 'audio.wav')

    try {
      const res  = await fetch('/ai_modules/stt', { method: 'POST', body: form })
      const data = await res.json()
      const text = (data.text || '').trim()

      // 첫 발화에서 언어 감지 → 이후 대화 전체에 고정
      if (data.language && !detectedLangRef.current) {
        const raw    = data.language.slice(0, 2).toLowerCase()
        const locale = langToLocale(raw)   // ko/zh/ja 외 → 'en'
        detectedLangRef.current = locale
        sessionStorage.setItem('kiosk_detected_lang', locale)
        setLocale(locale)
      }

      if (text) {
        setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }])
        handleBotReply(text)
      }
    } catch (e) {
      console.error('[ChatPanel] STT error:', e)
    }
  }, [setLocale])  // eslint-disable-line react-hooks/exhaustive-deps

  // ─── TTS: MediaSource 스트리밍 재생 ─────────────────────────────────────────

  async function playTts(text) {
    if (!text || !activeRef.current) return

    let res
    try {
      res = await fetch('/ai_modules/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, format: 'mp3' }),
      })
      if (!res.ok) return
    } catch { return }

    const useMediaSource =
      typeof window.MediaSource !== 'undefined' &&
      MediaSource.isTypeSupported('audio/mpeg')

    if (!useMediaSource) {
      // 폴백: blob 전체 수신 후 재생
      try {
        const blob  = await res.blob()
        const url   = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audioRef.current = audio
        await new Promise(resolve => {
          audio.onended = resolve
          audio.onerror = resolve
          audio.play().catch(resolve)
        })
        URL.revokeObjectURL(url)
        audioRef.current = null
      } catch {}
      return
    }

    const mediaSource = new MediaSource()
    const audio       = new Audio()
    audioRef.current  = audio
    const objectUrl   = URL.createObjectURL(mediaSource)
    audio.src         = objectUrl

    await new Promise((resolve) => {
      mediaSource.addEventListener('sourceopen', async () => {
        let sb
        try { sb = mediaSource.addSourceBuffer('audio/mpeg') }
        catch { resolve(); return }

        const waitUpdate = () =>
          new Promise(r => sb.addEventListener('updateend', r, { once: true }))

        const reader = res.body.getReader()
        audio.play().catch(() => {})

        try {
          while (activeRef.current) {
            const { done, value } = await reader.read()
            if (done) {
              if (mediaSource.readyState === 'open') mediaSource.endOfStream()
              break
            }
            if (sb.updating) await waitUpdate()
            sb.appendBuffer(value)
            await waitUpdate()
          }
        } catch { /* 정지 중 스트림 오류 무시 */ }
      }, { once: true })

      audio.onended = resolve
      audio.onerror = resolve
    })

    URL.revokeObjectURL(objectUrl)
    audioRef.current = null
  }

  // ─── LLM: SSE 스트리밍 ───────────────────────────────────────────────────────

  async function handleBotReply(userText) {
    setIsTyping(true)
    isTypingRef.current = true
    vadRef.current?.pause()   // 봇 응답 중 VAD 일시 정지

    const msgId = `bot-${Date.now()}`
    setMessages(prev => [...prev, { id: msgId, role: 'bot', text: '' }])

    let replyText = ''
    try {
      const res = await fetch('/ai_modules/llm/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          input: userText,
          language: detectedLangRef.current ?? undefined,
        }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const parts = buffer.split('\n\n')
        buffer = parts.pop()

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.token) {
              replyText += data.token
              setMessages(prev =>
                prev.map(m => m.id === msgId ? { ...m, text: replyText } : m)
              )
            }
            if (data.done && data.output) {
              replyText = data.output
              setMessages(prev =>
                prev.map(m => m.id === msgId ? { ...m, text: replyText } : m)
              )
            }
          } catch { /* JSON 파싱 실패 무시 */ }
        }
      }
    } catch (e) {
      replyText = '죄송해요, 서버와 연결이 잠시 어려워요. 잠시 후 다시 말씀해 주세요.'
      setMessages(prev =>
        prev.map(m => m.id === msgId ? { ...m, text: replyText } : m)
      )
      console.error('[ChatPanel] LLM error:', e)
    }

    setIsTyping(false)
    isTypingRef.current = false

    if (!activeRef.current) return

    await playTts(replyText)

    // TTS 재생 완료 후 VAD 재개
    if (activeRef.current) {
      setTimeout(() => vadRef.current?.start(), 300)
    }
  }

  // ─── 마운트 / 언마운트 ────────────────────────────────────────────────────────

  useEffect(() => {
    activeRef.current = true
    // startOnLoad: true 이므로 별도 start() 불필요 — 언마운트 시 정리만 담당

    return () => {
      activeRef.current = false
      vadRef.current?.pause()
      if (audioRef.current) {
        try { audioRef.current.pause() } catch {}
        audioRef.current = null
      }
    }
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 렌더 ─────────────────────────────────────────────────────────────────────

  const isVadLoading = vad.loading
  const isVadErrored = !!vad.errored
  // 에러 내용을 콘솔에 출력해 원인 파악
  if (vad.errored) console.error('[VAD] 초기화 실패:', vad.errored)
  const isSpeaking   = vad.userSpeaking

  return (
    <div
      onClick={e => e.stopPropagation()}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <style>{CSS}</style>

      {/* 메시지 목록 */}
      <div
        ref={scrollRef}
        style={{
          flex: 1, overflowY: 'auto',
          padding: '12px 14px',
          display: 'flex', flexDirection: 'column', gap: 10,
        }}
      >
        {messages.map(msg => (
          <div
            key={msg.id}
            style={{ display: 'flex', justifyContent: msg.role === 'bot' ? 'flex-start' : 'flex-end' }}
          >
            <div style={{
              maxWidth: '76%',
              background: msg.role === 'bot' ? '#C8E0FF' : '#ffffff',
              color: '#1a1a1a',
              borderRadius: msg.role === 'bot' ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
              padding: '10px 14px',
              fontSize: 14, lineHeight: 1.55,
              boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
              whiteSpace: 'pre-wrap', wordBreak: 'keep-all',
            }}>
              {msg.text}
              {msg.role === 'bot' && isTyping && msg.text && (
                <span style={{
                  display: 'inline-block', width: 2, height: '1em',
                  background: '#555', marginLeft: 2, verticalAlign: 'text-bottom',
                  animation: 'chatBlink 1s infinite',
                }} />
              )}
            </div>
          </div>
        ))}

        {isTyping && messages[messages.length - 1]?.text === '' && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              background: '#C8E0FF', borderRadius: '4px 16px 16px 16px',
              padding: '12px 16px', boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
              display: 'flex', alignItems: 'center', gap: 2,
            }}>
              <span className="chat-dot" />
              <span className="chat-dot" />
              <span className="chat-dot" />
            </div>
          </div>
        )}
      </div>

      {/* 음성 인식 상태 표시 */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '8px 12px 12px', gap: 10, flexShrink: 0,
      }}>
        {isVadErrored ? (
          <span style={{ fontSize: 12, color: '#c00' }}>
            오류: {vad.errored?.message ?? String(vad.errored)}
          </span>
        ) : isVadLoading ? (
          <span style={{ fontSize: 13, color: '#aaa' }}>음성 인식 준비 중...</span>
        ) : isTyping ? (
          <span style={{ fontSize: 13, color: '#888' }}>답변 중...</span>
        ) : isSpeaking || listening ? (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 3, height: 20 }}>
              <span className="wave-bar" />
              <span className="wave-bar" />
              <span className="wave-bar" />
              <span className="wave-bar" />
              <span className="wave-bar" />
            </div>
            <span style={{ fontSize: 13, color: '#744032', fontWeight: 700 }}>듣고 있습니다...</span>
          </>
        ) : (
          <span style={{ fontSize: 13, color: '#aaa' }}>말씀해 주세요</span>
        )}
      </div>
    </div>
  )
}
