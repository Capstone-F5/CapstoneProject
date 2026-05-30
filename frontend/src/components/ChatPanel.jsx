import { useState, useEffect, useRef } from 'react'

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

// Chrome 은 동시 SpeechRecognition 인스턴스를 1 개만 허용한다.
// 다국어 자동 감지는 백엔드 Whisper(/ai_modules/stt) 로 이전 예정. 여기서는 한국어 단일.
const SR_LANG = 'ko-KR'

const SR = window.SpeechRecognition || window.webkitSpeechRecognition

const INIT_MESSAGES = [
  {
    id: 'init', role: 'bot',
    text: '안녕하세요! 저는 F BURGER 주문 도우미입니다 🍔\n메뉴 추천, 알레르기 정보, 주문 방법 등 궁금한 점을 말씀해 주세요.',
  },
]

// 브라우저 세션 단위로 고정되는 LLM 세션 ID (탭 닫으면 초기화).
function getSessionId() {
  const KEY = 'kiosk_llm_session_id'
  let sid = sessionStorage.getItem(KEY)
  if (!sid) {
    sid = (crypto.randomUUID?.() ?? `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`)
    sessionStorage.setItem(KEY, sid)
  }
  return sid
}

export default function ChatPanel({ onClose }) {
  const [messages,  setMessages]  = useState(INIT_MESSAGES)
  const [isTyping,  setIsTyping]  = useState(false)
  const [listening, setListening] = useState(false)
  const scrollRef   = useRef(null)
  const srRef       = useRef(null)   // { sr, abort() } — 현재 활성 SR
  const restartTimerRef = useRef(null)  // scheduleRestart 의 단일 타이머
  const activeRef   = useRef(true)
  const isTypingRef = useRef(false)
  const sessionIdRef = useRef(getSessionId())
  const audioRef    = useRef(null)   // 현재 재생 중 TTS — 정리용

  useEffect(() => { isTypingRef.current = isTyping }, [isTyping])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, isTyping])

  function scheduleRestart() {
    if (restartTimerRef.current) return  // 이미 예약돼 있으면 중복 예약 금지
    restartTimerRef.current = setTimeout(() => {
      restartTimerRef.current = null
      if (activeRef.current && !isTypingRef.current) startListening()
    }, 500)
  }

  function startListening() {
    if (!SR || !activeRef.current || isTypingRef.current) return
    // StrictMode 이중 마운트 등으로 SR 가 살아 있는데 또 호출되는 경우 차단.
    if (srRef.current?.sr) return

    const sr = new SR()
    sr.lang = SR_LANG
    sr.interimResults = false
    sr.maxAlternatives = 1

    let done = false
    const finalize = () => {
      if (done) return
      done = true
      // 자신이 현재 활성 SR 일 때만 ref 비움 (이미 다른 SR 로 교체됐을 가능성 가드)
      if (srRef.current?.sr === sr) srRef.current = null
      setListening(false)
    }

    sr.onresult = (e) => {
      finalize()
      const text = e.results[0]?.[0]?.transcript?.trim()
      if (!text) { scheduleRestart(); return }
      setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }])
      handleBotReply(text)
    }

    sr.onerror = (ev) => {
      if (ev.error && ev.error !== 'no-speech' && ev.error !== 'aborted') {
        // eslint-disable-next-line no-console
        console.warn('[ChatPanel] SR error:', ev.error)
      }
      finalize()
      scheduleRestart()
    }

    sr.onend = () => {
      if (done) return
      finalize()
      scheduleRestart()
    }

    srRef.current = { sr, abort: () => { try { sr.abort() } catch {} } }
    try {
      sr.start()
      setListening(true)
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('[ChatPanel] SR start failed:', e)
      finalize()
      scheduleRestart()
    }
  }

  // GPT 응답을 음성으로 재생. 재생이 끝나면(또는 실패하면) resolve.
  async function playTts(text) {
    if (!text || !activeRef.current) return
    try {
      const res = await fetch('/ai_modules/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, format: 'mp3' }),
      })
      if (!res.ok) return
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      await new Promise((resolve) => {
        audio.onended = resolve
        audio.onerror = resolve
        audio.play().catch(resolve)
      })
      URL.revokeObjectURL(url)
      audioRef.current = null
    } catch {
      // 네트워크/오디오 오류는 조용히 무시 — 텍스트는 이미 떠 있음
    }
  }

  async function handleBotReply(text) {
    setIsTyping(true)
    isTypingRef.current = true
    srRef.current?.abort()
    setListening(false)

    let replyText = ''
    try {
      const res = await fetch('/ai_modules/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          input: text,
        }),
      })
      if (!res.ok) {
        const detail = await res.text().catch(() => '')
        throw new Error(`HTTP ${res.status} ${detail.slice(0, 200)}`)
      }
      const data = await res.json()
      replyText = (data.output || '').trim()
      if (!replyText) replyText = '죄송해요, 응답을 받지 못했어요. 다시 말씀해 주시겠어요?'
    } catch (e) {
      replyText = '죄송해요, 서버와 연결이 잠시 어려워요. 잠시 후 다시 말씀해 주세요.'
      // eslint-disable-next-line no-console
      console.error('[ChatPanel] LLM error:', e)
    }

    if (!activeRef.current) return

    setMessages(prev => [...prev, {
      id: Date.now(), role: 'bot', text: replyText,
    }])
    setIsTyping(false)
    isTypingRef.current = false

    // 음성 재생이 끝난 뒤 다시 듣기 시작 (자기 목소리 인식 방지)
    await playTts(replyText)
    setTimeout(() => { if (activeRef.current) startListening() }, 300)
  }

  useEffect(() => {
    activeRef.current = true
    if (!SR) {
      setMessages(prev => [...prev, {
        id: 'no-sr', role: 'bot',
        text: '이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 브라우저를 사용해 주세요.',
      }])
      return
    }
    startListening()
    return () => {
      activeRef.current = false
      if (restartTimerRef.current) {
        clearTimeout(restartTimerRef.current)
        restartTimerRef.current = null
      }
      srRef.current?.abort()
      srRef.current = null
      if (audioRef.current) {
        try { audioRef.current.pause() } catch {}
        audioRef.current = null
      }
    }
  }, [])

  return (
    <div
      onClick={e => e.stopPropagation()}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <style>{CSS}</style>

      {/* ── 메시지 목록 ── */}
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
            </div>
          </div>
        ))}

        {isTyping && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              background: '#C8E0FF',
              borderRadius: '4px 16px 16px 16px',
              padding: '12px 16px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
              display: 'flex', alignItems: 'center', gap: 2,
            }}>
              <span className="chat-dot" />
              <span className="chat-dot" />
              <span className="chat-dot" />
            </div>
          </div>
        )}
      </div>

      {/* ── 음성 인식 상태 표시 ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '8px 12px 12px',
        gap: 10, flexShrink: 0,
      }}>
        {listening ? (
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
        ) : isTyping ? (
          <span style={{ fontSize: 13, color: '#888' }}>답변 중...</span>
        ) : (
          <span style={{ fontSize: 13, color: '#aaa' }}>잠시 후 음성 인식이 시작됩니다</span>
        )}
      </div>
    </div>
  )
}
