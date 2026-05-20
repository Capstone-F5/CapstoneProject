import { useState, useEffect, useRef } from 'react'
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

// 4개 언어를 동시에 시작해 먼저 인식되는 언어로 자동 전환 (레이싱)
const LANG_CONFIGS = [
  { srLang: 'ko-KR', locale: 'ko' },
  { srLang: 'en-US', locale: 'en' },
  { srLang: 'zh-CN', locale: 'zh' },
  { srLang: 'ja-JP', locale: 'ja' },
]

const SR = window.SpeechRecognition || window.webkitSpeechRecognition

const INIT_MESSAGES = [
  {
    id: 'init', role: 'bot',
    text: '안녕하세요! 저는 F BURGER 주문 도우미입니다 🍔\n메뉴 추천, 알레르기 정보, 주문 방법 등 궁금한 점을 말씀해 주세요.',
  },
]

export default function ChatPanel({ onClose }) {
  const { setLocale } = useLocale()
  const [messages,  setMessages]  = useState(INIT_MESSAGES)
  const [isTyping,  setIsTyping]  = useState(false)
  const [listening, setListening] = useState(false)
  const scrollRef   = useRef(null)
  const srRef       = useRef(null)   // { abort() } — aborts all racing instances
  const activeRef   = useRef(true)
  const isTypingRef = useRef(false)
  const settledRef  = useRef(false)  // true once any racing instance wins

  useEffect(() => { isTypingRef.current = isTyping }, [isTyping])

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, isTyping])

  function scheduleRestart() {
    setTimeout(() => {
      if (activeRef.current && !isTypingRef.current) startListening()
    }, 500)
  }

  function startListening() {
    if (!SR || !activeRef.current || isTypingRef.current) return

    settledRef.current = false
    setListening(true)

    const instances = []
    let doneCount = 0

    LANG_CONFIGS.forEach(({ srLang, locale: detectedLocale }) => {
      const sr = new SR()
      sr.lang = srLang
      sr.interimResults = false
      sr.maxAlternatives = 1

      sr.onresult = (e) => {
        if (settledRef.current) return
        settledRef.current = true
        instances.forEach(s => { try { s.abort() } catch {} })
        setListening(false)

        const text = e.results[0]?.[0]?.transcript?.trim()
        if (!text) { scheduleRestart(); return }

        // 인식된 언어로 앱 로케일 자동 전환
        setLocale(detectedLocale)

        setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }])
        handleBotReply(text)
      }

      const onDone = () => {
        doneCount++
        if (doneCount >= LANG_CONFIGS.length && !settledRef.current) {
          settledRef.current = true
          setListening(false)
          scheduleRestart()
        }
      }

      sr.onend   = onDone
      sr.onerror = onDone
      instances.push(sr)
    })

    srRef.current = { abort: () => instances.forEach(s => { try { s.abort() } catch {} }) }
    instances.forEach(sr => { try { sr.start() } catch {} })
  }

  function handleBotReply(text) {
    setIsTyping(true)
    isTypingRef.current = true
    srRef.current?.abort()
    setListening(false)

    // ── LLM 연동 전 임시 응답 ──────────────────────────────────────
    // 실제 연동 시 이 setTimeout을 API 호출로 교체하세요:
    //   const res = await fetch('/api/chat', { method:'POST',
    //     body: JSON.stringify({ message: text }) })
    //   const { reply } = await res.json()
    // ──────────────────────────────────────────────────────────────
    setTimeout(() => {
      setIsTyping(false)
      isTypingRef.current = false
      setMessages(prev => [...prev, {
        id: Date.now(), role: 'bot',
        text: 'AI 서비스 연결을 준비 중입니다. 잠시 후 더 나은 서비스로 찾아오겠습니다! 😊\n불편하신 점은 직원에게 문의해 주세요.',
      }])
      setTimeout(() => { if (activeRef.current) startListening() }, 500)
    }, 900)
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
      srRef.current?.abort()
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
