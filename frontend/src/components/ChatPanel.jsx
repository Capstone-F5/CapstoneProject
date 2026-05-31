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

const SESSION_KEY = 'kiosk_llm_session_id'
const LANG_KEY    = 'kiosk_detected_lang'

function getSessionId() {
  // 페이지 로드마다 새 세션 — beforeunload 에서 삭제해 새로고침 시 초기화
  let sid = sessionStorage.getItem(SESSION_KEY)
  if (!sid) {
    sid = crypto.randomUUID?.() ?? `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`
    sessionStorage.setItem(SESSION_KEY, sid)
  }
  return sid
}

// 페이지 새로고침/닫기 시 세션·언어 초기화 (다음 로드에서 새 세션 시작)
window.addEventListener('beforeunload', () => {
  sessionStorage.removeItem(SESSION_KEY)
  sessionStorage.removeItem(LANG_KEY)
})

export default function ChatPanel({ onClose, isOpen = true, cart = [], screen = null, orderType = null, modalStateRef = null, onAction }) {
  const { setLocale } = useLocale()

  const [messages,  setMessages]  = useState(INIT_MESSAGES)
  const [isTyping,  setIsTyping]  = useState(false)
  const [listening, setListening] = useState(false)

  const scrollRef       = useRef(null)
  const activeRef       = useRef(true)
  const isTypingRef     = useRef(false)
  const sessionIdRef    = useRef(getSessionId())
  const audioRef        = useRef(null)    // 재생 중 Audio — 정리용
  // 스트리밍 TTS 큐: LLM 토큰이 쌓이는 동안 문장 단위로 TTS를 순차 재생
  const ttsQueueRef  = useRef([])   // 재생 대기 중인 텍스트 청크
  const ttsBusyRef   = useRef(false) // 현재 TTS 재생 중 여부
  const ttsBufRef    = useRef('')    // 아직 TTS에 보내지 않은 토큰 버퍼
  // 발화 직렬화: STT 진행 중(isProcessingRef) 또는 LLM 생성 중(isTypingRef) 동안
  // 새 발화는 pendingTextRef에 저장했다가 완료 후 처리
  const isProcessingRef = useRef(false)  // STT fetch 진행 중 플래그 (isTypingRef gap 차단)
  const pendingTextRef  = useRef(null)   // 대기 중인 발화 텍스트 (최신 1개 보관)
  // 첫 발화 감지 언어 — sessionStorage 연동으로 채팅 닫았다 열어도 유지
  // nav('start') 시 App에서 sessionStorage 항목 삭제 → 새 손님은 null로 시작
  const detectedLangRef = useRef(sessionStorage.getItem(LANG_KEY) || null)
  // props(cart/screen/onAction)는 speechEndHandlerRef의 stale closure 안에서 참조되므로 ref로 유지
  const cartRef       = useRef(cart)
  const screenRef2    = useRef(screen)
  const orderTypeRef  = useRef(orderType)
  const onActionRef   = useRef(onAction)
  cartRef.current     = cart
  screenRef2.current  = screen
  orderTypeRef.current = orderType
  onActionRef.current  = onAction

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
    // startOnLoad: false — 앱 시작 시 모델만 미리 로드, 마이크는 채팅 열 때만 시작
    startOnLoad: false,
    positiveSpeechThreshold: 0.7,  // 짧고 작은 발화도 감지 (0.8→0.7)
    negativeSpeechThreshold: 0.3,  // 말 끝을 조금 늦게 판정해 짧은 단어 보존
    minSpeechFrames: 2,            // "네", "매장" 등 짧은 단어가 misfire로 버려지지 않게 (4→2)
    preSpeechPadFrames: 5,         // 첫 음절 잘림 방지 (~160ms 선행 패딩)
    redemptionFrames: 12,          // 짧은 끊김에 말 끝 조기 종료 방지
    workletURL: '/vad.worklet.bundle.min.js',
    modelURL: '/silero_vad.onnx',
    onSpeechStart: () => {
      if (activeRef.current && !isTypingRef.current) {
        setListening(true)
        window.dispatchEvent(new Event('gesture-activity'))  // 말하는 순간 idle 타이머 리셋
        // 끼어들기: 재생 중인 TTS와 대기 큐 모두 즉시 취소
        clearTtsQueue()
      }
    },
    onSpeechEnd: (audio) => speechEndHandlerRef.current?.(audio),
    onVADMisfire: () => setListening(false),
  })

  // vadRef 항상 최신 유지
  useEffect(() => { vadRef.current = vad }, [vad])

  // speechEndHandlerRef 업데이트 — isTyping·detectedLang 등 최신 상태 참조
  speechEndHandlerRef.current = useCallback(async (audio) => {
    setListening(false)
    if (!activeRef.current) return

    // 이미 STT 처리 중이면 건너뜀 (동시 STT 방지)
    // isTypingRef(LLM 생성 중)는 여기서 차단하지 않음 — STT 후 pendingTextRef에 큐잉
    if (isProcessingRef.current) return

    // Float32Array(16 kHz) → WAV Blob → 백엔드 Whisper
    const wavBlob = new Blob([utils.encodeWAV(audio)], { type: 'audio/wav' })
    // ~30ms(약 1KB) 미만만 차단 — 짧은 단어("네", "응")는 통과 (이전 2000→1000)
    if (wavBlob.size < 1000) return

    // STT 구간 시작 — 이 플래그로 동일 구간에 다른 발화가 끼어드는 것을 차단
    isProcessingRef.current = true

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
        sessionStorage.setItem(LANG_KEY, locale)
        setLocale(locale)
      }

      if (text) {
        window.dispatchEvent(new Event('gesture-activity'))  // idle 타이머 리셋
        setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }])

        // 시작 화면에서 뭔 말을 하든 → 주문 화면으로 자동 이동
        if (screenRef2.current === 'start') {
          onActionRef.current?.({ type: 'navigate', screen: 'orderType' })
        }

        // STT 완료 시점에 LLM이 이미 다른 응답을 생성 중이면 큐에 저장
        if (isTypingRef.current) {
          pendingTextRef.current = text   // 최신 발화 1개 보관 (이전 대기 발화는 덮어씀)
        } else {
          handleBotReply(text)  // handleBotReply가 isTypingRef를 즉시 true로 설정
        }
      }
    } catch (e) {
      console.error('[ChatPanel] STT error:', e)
    } finally {
      isProcessingRef.current = false   // STT 구간 종료
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

  // ─── 스트리밍 TTS 큐 ─────────────────────────────────────────────────────────
  // LLM 응답과 동시에 문장 단위로 TTS를 순차 재생해 체감 지연을 줄인다.

  // 문장 경계 패턴 (한국어 포함)
  const TTS_BOUNDARY = /[.!?。\n]/

  // 큐 초기화 (새 요청 시작 또는 끼어들기)
  function clearTtsQueue() {
    ttsQueueRef.current = []
    ttsBusyRef.current  = false
    ttsBufRef.current   = ''
    if (audioRef.current) {
      try { audioRef.current.pause() } catch {}
      audioRef.current = null
    }
  }

  // 큐에서 꺼내 순차 재생
  async function drainTtsQueue() {
    if (!activeRef.current || ttsQueueRef.current.length === 0) {
      ttsBusyRef.current = false
      return
    }
    ttsBusyRef.current = true
    const chunk = ttsQueueRef.current.shift()
    try { await playTts(chunk) } catch {}
    if (activeRef.current) drainTtsQueue()
    else ttsBusyRef.current = false
  }

  // 텍스트를 큐에 추가하고 재생 시작
  function pushTts(text) {
    const t = (text ?? '').trim()
    if (t.length < 5) return   // 너무 짧은 청크는 무시
    ttsQueueRef.current.push(t)
    if (!ttsBusyRef.current) drainTtsQueue()
  }

  // 토큰 버퍼에서 완성된 문장을 TTS로 플러시
  // force=true: 남은 버퍼 전체를 즉시 보냄 (LLM 완료 시)
  function flushTtsBuf(force = false) {
    const buf = ttsBufRef.current
    if (!buf) return
    if (force) {
      pushTts(buf)
      ttsBufRef.current = ''
      return
    }
    // 마지막 문장 경계 위치 탐색
    let lastBound = -1
    for (let i = 0; i < buf.length; i++) {
      if (TTS_BOUNDARY.test(buf[i])) lastBound = i
    }
    if (lastBound >= 0) {
      pushTts(buf.slice(0, lastBound + 1))
      ttsBufRef.current = buf.slice(lastBound + 1).trimStart()
    }
  }

  // ─── LLM: SSE 스트리밍 ───────────────────────────────────────────────────────

  async function handleBotReply(userText) {
    // 이전 TTS 큐/오디오 정리 후 새 응답 시작
    clearTtsQueue()
    setIsTyping(true)
    isTypingRef.current = true
    window.dispatchEvent(new Event('gesture-activity'))
    vadRef.current?.pause()   // LLM 생성 중 VAD 일시 정지

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
          screen: screenRef2.current ?? undefined,
          order_type: orderTypeRef.current ?? undefined,
          cart: cartRef.current.length ? cartRef.current : undefined,
          modal_state: (() => {
            const ms = modalStateRef?.current
            if (!ms?.open) return undefined
            const s = ms.getState?.()
            return s ? { menu_id: s.menu_id, name: s.name, item_type: s.item_type,
                         qty: s.qty, exclusion: s.exclusion, side: s.side, drink: s.drink } : undefined
          })(),
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
              ttsBufRef.current += data.token   // ← 토큰을 TTS 버퍼에 누적
              flushTtsBuf()                      // ← 문장 경계 감지 시 TTS 발행
              setMessages(prev =>
                prev.map(m => m.id === msgId ? { ...m, text: replyText } : m)
              )
            }
            if (data.action) {
              onActionRef.current?.(data.action)
            }
            if (data.done && data.output) {
              replyText = data.output
              flushTtsBuf(true)                  // ← 잔여 버퍼 강제 플러시
              setMessages(prev =>
                prev.map(m => m.id === msgId ? { ...m, text: replyText } : m)
              )
            }
          } catch { /* JSON 파싱 실패 무시 */ }
        }
      }
    } catch (e) {
      replyText = '죄송해요, 서버와 연결이 잠시 어려워요. 잠시 후 다시 말씀해 주세요.'
      flushTtsBuf(true)
      setMessages(prev =>
        prev.map(m => m.id === msgId ? { ...m, text: replyText } : m)
      )
      console.error('[ChatPanel] LLM error:', e)
    }

    setIsTyping(false)
    isTypingRef.current = false

    if (!activeRef.current) return

    // LLM 완료 → VAD 재개
    setTimeout(() => vadRef.current?.start(), 100)

    // 대기 중인 발화가 있으면 이어서 처리
    const pending = pendingTextRef.current
    if (pending) {
      pendingTextRef.current = null
      setMessages(prev => {
        // 이미 메시지 목록에 있는지 확인 (중복 방지)
        const exists = prev.some(m => m.role === 'user' && m.text === pending)
        return exists ? prev : [...prev, { id: Date.now(), role: 'user', text: pending }]
      })
      handleBotReply(pending)
    }
    // TTS는 drainTtsQueue()가 비동기로 처리
  }

  // ─── 채팅 열림/닫힘 → VAD start/pause ───────────────────────────────────────

  useEffect(() => {
    if (isOpen) {
      activeRef.current = true
      // 모델 로딩이 완료된 경우에만 start (로딩 중이면 로딩 완료 후 effect 재실행)
      if (!vad.loading) vadRef.current?.start()
    } else {
      activeRef.current = false
      vadRef.current?.pause()
      setListening(false)
      if (audioRef.current) {
        try { audioRef.current.pause() } catch {}
        audioRef.current = null
      }
    }
  }, [isOpen, vad.loading])  // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 채팅 열릴 때 인사말 TTS (VAD 유지 → 끼어들기 가능) ───────────────────────

  useEffect(() => {
    if (!isOpen) return
    const timer = setTimeout(() => {
      if (!activeRef.current) return
      // VAD를 멈추지 않고 재생 — onSpeechStart에서 TTS 중단 처리
      playTts('안녕하세요! F버거 주문 도우미입니다. 메뉴 추천, 주문 방법 등 궁금한 점을 말씀해 주세요.')
    }, 300)
    return () => clearTimeout(timer)
  }, [isOpen])  // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 세션 리셋 이벤트 (nav('start') 호출 시) ─────────────────────────────────

  useEffect(() => {
    const handleReset = async () => {
      // 백엔드 LLM 메모리 초기화
      const oldSid = sessionIdRef.current
      try {
        await fetch(`/ai_modules/llm/reset?session_id=${oldSid}`, { method: 'POST' })
      } catch {}

      // 새 세션 ID 발급
      const newSid = crypto.randomUUID?.() ?? `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`
      sessionIdRef.current = newSid
      sessionStorage.setItem(SESSION_KEY, newSid)

      // 프론트 상태 초기화
      detectedLangRef.current = null
      setMessages(INIT_MESSAGES)
      setIsTyping(false)
      isTypingRef.current = false
    }
    window.addEventListener('kiosk-session-reset', handleReset)
    return () => window.removeEventListener('kiosk-session-reset', handleReset)
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
