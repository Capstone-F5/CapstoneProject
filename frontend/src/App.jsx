import { useState, useCallback, useRef, useEffect } from 'react'
import { useGesture } from './hooks/useGesture'
import { LocaleProvider, useLocale } from './i18n/LocaleContext'
import CollectTool from './tools/CollectTool'
import StartScreen from './screens/StartScreen'
import OrderTypeScreen from './screens/OrderTypeScreen'
import MenuScreen from './screens/MenuScreen'
import CartScreen from './screens/CartScreen'
import PaymentScreen from './screens/PaymentScreen'
import CompletionScreen from './screens/CompletionScreen'
import CardPaymentScreen from './screens/CardPaymentScreen'
import PayPaymentScreen from './screens/PayPaymentScreen'
import CashPaymentScreen from './screens/CashPaymentScreen'
import ChatPanel from './components/ChatPanel'

// 제스처 키 → 표시 문자열 (컴포넌트 외부 상수)
const GESTURE_LABELS = {
  swipe_right: '→ 다음',
  swipe_left:  '← 이전',
  swipe_up:    '↑ 위로',
  swipe_down:  '↓ 아래로',
  ok:          '✓ 확인',
  finger_1:    '☝ 1',
  finger_2:    '✌ 2',
  finger_3:    '3',
  finger_4:    '4',
  finger_5:    '✋ 5',
}

const _isCollect = new URLSearchParams(window.location.search).has('collect')

// LocaleProvider 바깥에서는 useLocale() 호출 불가 → AppContent로 분리
function AppContent() {
  const { setLocale } = useLocale()
  const [screen,    setScreen]    = useState('start')
  const [cart,      setCart]      = useState([])
  const [orderType, setOrderType] = useState(null)
  const [orderNum,  setOrderNum]  = useState(null)
  const [chatOpen,  setChatOpen]  = useState(false)

  // 손동작 인식 On/Off & PiP 표시 (localStorage 영구 저장)
  const [gestureEnabled, setGestureEnabled] = useState(() => {
    const v = localStorage.getItem('gestureEnabled')
    return v === null ? true : v === 'true'
  })
  const [pipEnabled, setPipEnabled] = useState(() => {
    return localStorage.getItem('pipEnabled') === 'true'
  })
  useEffect(() => { localStorage.setItem('gestureEnabled', String(gestureEnabled)) }, [gestureEnabled])
  useEffect(() => { localStorage.setItem('pipEnabled',     String(pipEnabled))     }, [pipEnabled])

  // PiP 캔버스 — useGesture가 매 프레임 카메라 영상 + 관절을 직접 그림
  const pipCanvasRef = useRef(null)

  // 포인터 — DOM 직접 조작으로 React 리렌더 없이 30fps 업데이트
  const pointerRef    = useRef(null)   // 최신 위치 { x, y }
  const pointerDivRef = useRef(null)   // 커서 DOM 노드

  // OK 로딩 링 — DOM 직접 조작
  const okRingRef = useRef(null)
  const okRafRef  = useRef(null)

  // 엣지 존 — DOM 직접 조작
  const EDGE_MARGIN    = 0.10   // 화면 크기의 10%
  const EDGE_MAX_SPEED = 500    // px/s (최대 강도일 때)
  const edgeTopRef    = useRef(null)
  const edgeBottomRef = useRef(null)
  const edgeLeftRef   = useRef(null)
  const edgeRightRef  = useRef(null)
  const edgeStateRef  = useRef({ left: 0, right: 0, top: 0, bottom: 0 })
  const edgeRafRef    = useRef(null)
  const edgeLastTRef  = useRef(null)

  // MenuScreen 스와이프 / 모달 imperative 핸들러
  const menuSwipeRef = useRef(null)
  const menuModalRef = useRef(null)

  // 현재 화면을 ref로 유지 — handleGesture 콜백 재생성 없이 참조
  const screenRef = useRef(screen)
  useEffect(() => { screenRef.current = screen }, [screen])

  // 화면별 제스처 액션 — 렌더마다 최신 클로저를 갱신
  const gestureActionsRef = useRef({})
  gestureActionsRef.current = {
    orderType: {
      dineIn:  () => { setOrderType('dine-in'); setScreen('menu') },
      takeout: () => { setOrderType('takeout');  setScreen('menu') },
    },
  }

  // 감지된 제스처 표시용 (일시적 알림)
  const [gestureLabel, setGestureLabel] = useState(null)
  const labelTimerRef = useRef(null)

  const showLabel = useCallback((text) => {
    setGestureLabel(text)
    clearTimeout(labelTimerRef.current)
    labelTimerRef.current = setTimeout(() => setGestureLabel(null), 1200)
  }, [])

  // ── 포인터 민감도 ────────────────────────────────────────────────────────
  // 앵커 기반 매핑을 useGesture 에서 처리하므로 1.0 고정.
  // 이동 범위는 useGesture.js 의 ANCHOR_WINDOW_HALF 로 조절.
  const POINTER_SENS_X = 1.0
  const POINTER_SENS_Y = 1.0

  // 정규화 좌표(MediaPipe 0~1, 좌우 반전 전) → 화면 픽셀로 변환
  const normToScreen = useCallback(({ x, y }) => {
    const nx = (1 - x) - 0.5   // 좌우 반전 후 중심 기준
    const ny = y - 0.5
    return {
      x: (0.5 + nx * POINTER_SENS_X) * window.innerWidth,
      y: (0.5 + ny * POINTER_SENS_Y) * window.innerHeight,
    }
  }, [])

  // 제스처 활동 → idle 타이머 리셋용 커스텀 이벤트 (2초 스로틀)
  const lastActivityRef = useRef(0)
  const dispatchActivity = useCallback(() => {
    const now = Date.now()
    if (now - lastActivityRef.current > 2000) {
      lastActivityRef.current = now
      window.dispatchEvent(new Event('gesture-activity'))
    }
  }, [])

  // 엣지 인디케이터 opacity 초기화
  const clearEdge = useCallback(() => {
    edgeStateRef.current = { left: 0, right: 0, top: 0, bottom: 0 }
    if (edgeTopRef.current)    edgeTopRef.current.style.opacity    = 0
    if (edgeBottomRef.current) edgeBottomRef.current.style.opacity = 0
    if (edgeLeftRef.current)   edgeLeftRef.current.style.opacity   = 0
    if (edgeRightRef.current)  edgeRightRef.current.style.opacity  = 0
  }, [])

  // 포인터: useGesture 의 onPointer 콜백 — React state 없이 DOM 직접 업데이트
  const handlePointer = useCallback((norm) => {
    if (!norm) {
      pointerRef.current = null
      // opacity 만 끄기 — DOM은 유지해서 재등장 시 위치가 부드럽게 트랜지션됨
      if (pointerDivRef.current) pointerDivRef.current.style.opacity = '0'
      clearEdge()
      return
    }
    const p = normToScreen(norm)
    pointerRef.current = p
    const d = pointerDivRef.current
    if (d) {
      d.style.left    = `${p.x - 14}px`
      d.style.top     = `${p.y - 14}px`
      d.style.opacity = '1'
    }

    // ── 엣지 존 감지 ──────────────────────────────────────────────────────
    const nx = p.x / window.innerWidth
    const ny = p.y / window.innerHeight
    // 강도: 존 경계에서 0, 화면 끝에서 1
    const eL = Math.max(0, (EDGE_MARGIN - nx)       / EDGE_MARGIN)
    const eR = Math.max(0, (EDGE_MARGIN - (1 - nx)) / EDGE_MARGIN)
    const eT = Math.max(0, (EDGE_MARGIN - ny)       / EDGE_MARGIN)
    const eB = Math.max(0, (EDGE_MARGIN - (1 - ny)) / EDGE_MARGIN)

    if (edgeTopRef.current)    edgeTopRef.current.style.opacity    = eT
    if (edgeBottomRef.current) edgeBottomRef.current.style.opacity = eB
    if (edgeLeftRef.current)   edgeLeftRef.current.style.opacity   = eL
    if (edgeRightRef.current)  edgeRightRef.current.style.opacity  = eR

    edgeStateRef.current = { left: eL, right: eR, top: eT, bottom: eB }

    // 엣지 자동 스크롤 루프 — 이미 실행 중이면 재시작 안 함
    if ((eL + eR + eT + eB) > 0 && !edgeRafRef.current) {
      edgeLastTRef.current = null
      const tick = (t) => {
        const cur = pointerRef.current
        if (!cur) { edgeRafRef.current = null; return }
        const e = edgeStateRef.current
        if (e.left + e.right + e.top + e.bottom === 0) { edgeRafRef.current = null; return }

        const dt = edgeLastTRef.current !== null ? (t - edgeLastTRef.current) / 1000 : 0
        edgeLastTRef.current = t

        if (dt > 0) {
          const dx = (e.right - e.left) * EDGE_MAX_SPEED * dt
          const dy = (e.bottom - e.top) * EDGE_MAX_SPEED * dt
          // 커서 위치 아래의 스크롤 가능한 요소 탐색
          let el = document.elementFromPoint(cur.x, cur.y)
          let scrolled = false
          while (el && el !== document.documentElement) {
            const cs   = window.getComputedStyle(el)
            const canY = (cs.overflowY === 'auto' || cs.overflowY === 'scroll') && el.scrollHeight > el.clientHeight
            const canX = (cs.overflowX === 'auto' || cs.overflowX === 'scroll') && el.scrollWidth  > el.clientWidth
            if (canY || canX) {
              if (canY) el.scrollTop  += dy
              if (canX) el.scrollLeft += dx
              scrolled = true
              break
            }
            el = el.parentElement
          }
          if (!scrolled) window.scrollBy(0, dy)
        }

        edgeRafRef.current = requestAnimationFrame(tick)
      }
      edgeRafRef.current = requestAnimationFrame(tick)
    }

    dispatchActivity()
  }, [normToScreen, dispatchActivity, clearEdge])

  // OK 이동 취소 임계값 (screen px) — 이 이상 움직이면 링 취소
  const OK_MOVE_THRESHOLD = 80

  // OK: 손을 충분히 안 움직이면 0.5초 후 클릭 — DOM 직접 조작으로 rAF 리렌더 없음
  const fireOk = useCallback(() => {
    if (okRafRef.current !== null) return

    const p = pointerRef.current
    if (!p) return

    const startX   = p.x
    const startY   = p.y
    const start    = performance.now()
    const DURATION = 500
    const ring     = okRingRef.current

    if (ring) {
      ring.style.display    = 'block'
      ring.style.left       = `${startX - 28}px`
      ring.style.top        = `${startY - 28}px`
      ring.style.background = `conic-gradient(rgba(80,210,255,0.95) 0deg, rgba(255,255,255,0.18) 0deg)`
    }

    const tick = (now) => {
      const cur = pointerRef.current
      if (!cur || Math.hypot(cur.x - startX, cur.y - startY) > OK_MOVE_THRESHOLD) {
        okRafRef.current = null
        if (ring) ring.style.display = 'none'
        return
      }

      const progress = Math.min((now - start) / DURATION, 1)
      if (ring) ring.style.background =
        `conic-gradient(rgba(80,210,255,0.95) ${progress * 360}deg, rgba(255,255,255,0.18) 0deg)`

      if (progress < 1) {
        okRafRef.current = requestAnimationFrame(tick)
      } else {
        okRafRef.current = null
        if (ring) ring.style.display = 'none'
        const el = document.elementFromPoint(startX, startY)
        if (el) el.click()
      }
    }
    okRafRef.current = requestAnimationFrame(tick)
  }, [])

  // 포인터 위치의 가장 가까운 스크롤 가능 요소를 스크롤
  const scrollAtPointer = useCallback((dy) => {
    const p = pointerRef.current
    let el = p ? document.elementFromPoint(p.x, p.y) : null
    while (el && el !== document.documentElement) {
      const { overflowY } = window.getComputedStyle(el)
      if ((overflowY === 'auto' || overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
        el.scrollBy({ top: dy, behavior: 'smooth' })
        return
      }
      el = el.parentElement
    }
    window.scrollBy({ top: dy, behavior: 'smooth' })
  }, [])

  // 테스트용 HUD 상태
  const [gestureHud, setGestureHud] = useState(null)

  const handleGesture = useCallback(({ gesture, hands, total_fingers }) => {
    // HUD 업데이트 (포인터는 onPointer 가 처리, 제스처는 showLabel 이 갱신)
    setGestureHud({
      left:  hands?.left  ? `${hands.left.finger_count}개`  : '-',
      right: hands?.right ? `${hands.right.finger_count}개` : '-',
      total: total_fingers ?? 0,
    })

    if (!gesture) return

    const currentScreen = screenRef.current

    // ── 랜딩 페이지: 커서 + OK만 ─────────────────────
    if (currentScreen === 'start') {
      if (gesture === 'ok') { fireOk(); showLabel(GESTURE_LABELS.ok) }
      return
    }

    // ── 식사 장소 선택: OK(포인터 클릭) + 1(매장) + 2(포장) ──
    if (currentScreen === 'orderType') {
      const { dineIn, takeout } = gestureActionsRef.current.orderType
      const activeHand  = hands?.right || hands?.left
      const fingerCount = activeHand?.finger_count ?? -1
      if      (gesture === 'ok')                              { fireOk(); showLabel(GESTURE_LABELS.ok) }
      else if (gesture === 'finger_1' && fingerCount <= 1)   { dineIn();  showLabel('☝ 매장') }
      else if (gesture === 'finger_2' && fingerCount >= 2)   { takeout(); showLabel('✌ 포장') }
      return
    }

    // ── 나머지 모든 페이지 ────────────────────────────
    if (gesture === 'ok') {
      fireOk()
      showLabel(GESTURE_LABELS.ok)
      return
    }

    if (gesture === 'swipe_up') {
      scrollAtPointer(-260)
      showLabel(GESTURE_LABELS.swipe_up)
      return
    }

    if (gesture === 'swipe_down') {
      scrollAtPointer(260)
      showLabel(GESTURE_LABELS.swipe_down)
      return
    }

    // 메뉴 화면 모달 제스처 (단품/세트 선택) — 스와이프/스크롤보다 먼저 처리
    if (currentScreen === 'menu' && menuModalRef.current) {
      if (gesture === 'finger_1') { menuModalRef.current('single'); showLabel('☝ 단품'); return }
      if (gesture === 'finger_2') { menuModalRef.current('set');    showLabel('✌ 세트');  return }
    }

    // 메뉴 화면 좌우 스와이프 → 페이지/탭 전환
    if (currentScreen === 'menu' && (gesture === 'swipe_left' || gesture === 'swipe_right')) {
      menuSwipeRef.current?.(gesture === 'swipe_right' ? 'left' : 'right')
      showLabel(GESTURE_LABELS[gesture])
      return
    }

    if (gesture.startsWith('swipe_')) showLabel(GESTURE_LABELS[gesture])
  }, [showLabel, fireOk, scrollAtPointer])

  useGesture({
    onPointer:    handlePointer,
    onGesture:    handleGesture,
    enabled:      gestureEnabled,
    pipCanvasRef: gestureEnabled && pipEnabled ? pipCanvasRef : null,
  })

  // 손동작 OFF: 잔여 포인터/OK 링 UI 즉시 숨김
  useEffect(() => {
    if (gestureEnabled) return
    pointerRef.current = null
    if (pointerDivRef.current) pointerDivRef.current.style.opacity = '0'
    if (okRingRef.current)     okRingRef.current.style.display     = 'none'
    if (okRafRef.current) { cancelAnimationFrame(okRafRef.current); okRafRef.current = null }
    if (edgeRafRef.current) { cancelAnimationFrame(edgeRafRef.current); edgeRafRef.current = null }
    edgeStateRef.current = { left: 0, right: 0, top: 0, bottom: 0 }
  }, [gestureEnabled])


  const nav = (s) => {
    if (s === 'start') {
      // 새 손님 시작 — 언어·세션 초기화
      setLocale('ko')
      sessionStorage.removeItem('kiosk_detected_lang')
      sessionStorage.removeItem('kiosk_llm_session_id')
    }
    setScreen(s)
  }

  const addToCart = (item) => {
    setCart(prev => {
      const key = `${item.id}-${item.type}-${item.exclusion}-${item.side ?? ''}-${item.drink ?? ''}`
      const existing = prev.find(c => c.key === key)
      if (existing) {
        return prev.map(c => c.key === key ? { ...c, qty: c.qty + item.qty } : c)
      }
      return [...prev, { ...item, key, cartId: Date.now() + Math.random() }]
    })
  }

  const updateQty = (cartId, qty) => {
    if (qty <= 0) setCart(prev => prev.filter(c => c.cartId !== cartId))
    else setCart(prev => prev.map(c => c.cartId === cartId ? { ...c, qty } : c))
  }

  const clearCart = () => setCart([])

  const total = cart.reduce((sum, c) => sum + c.unitPrice * c.qty, 0)
  const props = { cart, total, addToCart, updateQty, clearCart, nav, setOrderNum, orderType, chatOpen }

  const startProps = {
    ...props,
    gestureEnabled, setGestureEnabled,
    pipEnabled,     setPipEnabled,
  }

  const screens = {
    start:       <StartScreen {...startProps} />,
    orderType:   <OrderTypeScreen nav={nav} setOrderType={setOrderType} />,
    menu:        <MenuScreen {...props} swipeRef={menuSwipeRef} modalRef={menuModalRef} />,
    cart:        <CartScreen {...props} />,
    payment:     <PaymentScreen {...props} />,
    complete:    <CompletionScreen orderNum={orderNum} nav={nav} />,
    cardPayment: <CardPaymentScreen {...props} />,
    payPayment:  <PayPaymentScreen {...props} />,
    cashPayment: <CashPaymentScreen {...props} />,
  }

  return (
    <>
        {/* ── 테스트 HUD (좌측 하단) ── */}
        {gestureHud && (
          <div style={{
            position: 'fixed', bottom: 16, left: 16,
            background: 'rgba(0,0,0,0.75)', color: '#fff',
            padding: '10px 16px', borderRadius: 10,
            fontSize: 13, lineHeight: 1.8,
            fontFamily: 'monospace', pointerEvents: 'none', zIndex: 9002,
          }}>
            <div>왼손 &nbsp;: {gestureHud.left}</div>
            <div>오른손: {gestureHud.right}</div>
            <div>합계 &nbsp;: {gestureHud.total}개</div>
            <div style={{ color: gestureLabel ? '#7fff7f' : '#888' }}>
              제스처: {gestureLabel ?? '-'}
            </div>
          </div>
        )}

        {/* ── 제스처 포인터 — DOM 직접 조작, React 리렌더 없음 ── */}
        <div ref={pointerDivRef} style={{
          position: 'fixed',
          left: -100, top: -100,
          width: 28, height: 28,
          borderRadius: '50%',
          background: 'rgba(255, 80, 80, 0.55)',
          border: '2.5px solid rgba(255,255,255,0.85)',
          pointerEvents: 'none',
          zIndex: 9000,
          opacity: 0,
          // 등장/사라짐만 트랜지션 (위치는 이미 OneEuro로 스무딩됨)
          transition: 'opacity 0.18s ease-out',
          willChange: 'left, top, opacity',
        }} />

        {/* ── 카메라 PiP — 우측 상단 반투명 미리보기 (실제 인식 영역 + 관절) ── */}
        {gestureEnabled && pipEnabled && (
          <div style={{
            position: 'fixed',
            top: 16, right: 16,
            width: 200,
            borderRadius: 10,
            overflow: 'hidden',
            border: '1.5px solid rgba(255,255,255,0.45)',
            boxShadow: '0 4px 18px rgba(0,0,0,0.45)',
            opacity: 0.82,
            background: '#000',
            pointerEvents: 'none',
            zIndex: 9003,
          }}>
            {/* canvas 비율은 카메라 해상도에 따라 자동 — width:100% + height:auto 로 왜곡 없이 */}
            <canvas
              ref={pipCanvasRef}
              style={{ display: 'block', width: '100%', height: 'auto' }}
            />
          </div>
        )}

        {/* ── OK 로딩 링 — DOM 직접 조작 ── */}
        <div ref={okRingRef} style={{
          display: 'none',
          position: 'fixed',
          width: 56, height: 56,
          borderRadius: '50%',
          pointerEvents: 'none',
          zIndex: 9004,
        }}>
          <div style={{
            position: 'absolute', inset: 7,
            borderRadius: '50%',
            background: 'rgba(0,0,0,0.55)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'rgba(255,255,255,0.9)',
            fontSize: 14, fontWeight: 700,
          }}>✓</div>
        </div>

        {/* ── 제스처 라벨 알림 ── */}
        {gestureLabel && (
          <div style={{
            position: 'fixed',
            top: 24, left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(0,0,0,0.72)',
            color: '#fff',
            padding: '8px 22px',
            borderRadius: 24,
            fontSize: 18,
            fontWeight: 600,
            pointerEvents: 'none',
            zIndex: 9001,
          }}>
            {gestureLabel}
          </div>
        )}

        {/* ── 메인 레이아웃 ── */}
        <div style={{
          display: 'flex', flexDirection: 'column',
          height: '100dvh', minHeight: '100vh',
          overflow: 'hidden',
        }}>
          {/* 화면 영역 — 채팅창이 열리면 자동으로 줄어듦 */}
          <div style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
            {screens[screen] ?? screens.start}
          </div>

          {/* 채팅 패널 — 하단에서 슬라이드업 */}
          <div style={{
            flexShrink: 0,
            height: chatOpen ? '33vh' : 0,
            overflow: 'hidden',
            transition: 'height 0.35s ease',
            background: '#e0e0e0',
            borderTop: chatOpen ? '1.5px solid #bbb' : 'none',
          }}>
            {chatOpen && <ChatPanel onClose={() => setChatOpen(false)} />}
          </div>
        </div>

        {/* ── 채팅 FAB — 항상 최상단에 고정 ── */}
        {screen === 'start' && (
          <button
            onClick={() => setChatOpen(o => !o)}
            style={{
              position: 'fixed',
              bottom: chatOpen ? 'calc(33vh + 20px)' : 20,
              right: 20,
              zIndex: 500,
              width: 60, height: 60,
              borderRadius: '50%',
              border: '2px solid rgba(255,255,255,0.65)',
              background: chatOpen ? 'rgba(50,50,50,0.92)' : 'rgba(116,64,50,0.92)',
              color: '#fff',
              fontSize: chatOpen ? 20 : 24,
              cursor: 'pointer',
              boxShadow: '0 4px 20px rgba(0,0,0,0.38)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'bottom 0.35s ease, background 0.2s',
            }}
            title={chatOpen ? '채팅 닫기' : '대화형 주문 도우미'}
          >
            {chatOpen ? '✕' : '💬'}
          </button>
        )}
      </>
  )
}

export default _isCollect ? CollectTool : function App() {
  return (
    <LocaleProvider>
      <AppContent />
    </LocaleProvider>
  )
}
