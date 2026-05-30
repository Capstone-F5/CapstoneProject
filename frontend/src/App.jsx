import { useState, useCallback, useRef, useEffect } from 'react'
import { useGesture } from './hooks/useGesture'
import { LocaleProvider } from './i18n/LocaleContext'
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

export default _isCollect ? CollectTool : function App() {
  const [screen,    setScreen]    = useState('start')
  const [cart,      setCart]      = useState([])
  const [orderType, setOrderType] = useState(null)
  const [orderNum,  setOrderNum]  = useState(null)
  const [chatOpen,  setChatOpen]  = useState(false)

  // 제스처 포인터 (손바닥 중심 위치)
  const [pointer, setPointer] = useState(null)   // { x, y } screen px
  const pointerRef = useRef(null)                // 최신 포인터 위치 (콜백에서 참조)

  // OK 로딩 링 (0.5초 채우면 클릭)
  const [okPending, setOkPending] = useState(null)  // { x, y } — 링 고정 위치
  const [okProgress, setOkProgress] = useState(0)  // 0→1
  const okRafRef = useRef(null)

  // MenuScreen 스와이프 imperative 핸들러
  const menuSwipeRef = useRef(null)

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

  // 포인터: useGesture 의 onPointer 콜백 — 매 MediaPipe 프레임마다 즉시 호출
  const handlePointer = useCallback((norm) => {
    if (!norm) {
      setPointer(null)
      pointerRef.current = null
      return
    }
    const p = normToScreen(norm)
    setPointer(p)
    pointerRef.current = p
    dispatchActivity()
  }, [normToScreen, dispatchActivity])

  // OK 이동 취소 임계값 (screen px) — 이 이상 움직이면 링 취소
  const OK_MOVE_THRESHOLD = 80

  // OK: 손을 충분히 안 움직이면 0.5초 후 클릭
  // — 이미 진행 중이면 재시작하지 않음 (쿨다운 재발화로 인한 리셋 방지)
  // — 매 프레임 손 이동 거리 체크, 임계값 초과 or 손 사라지면 취소
  const fireOk = useCallback(() => {
    if (okRafRef.current !== null) return  // 이미 진행 중

    const p = pointerRef.current
    if (!p) return

    const startX = p.x
    const startY = p.y
    const start  = performance.now()
    const DURATION = 500

    setOkPending({ x: startX, y: startY })
    setOkProgress(0)

    const tick = (now) => {
      const cur = pointerRef.current

      // 손 사라짐 or 너무 많이 움직임 → 취소
      if (!cur) {
        okRafRef.current = null
        setOkPending(null)
        setOkProgress(0)
        return
      }
      const dist = Math.hypot(cur.x - startX, cur.y - startY)
      if (dist > OK_MOVE_THRESHOLD) {
        okRafRef.current = null
        setOkPending(null)
        setOkProgress(0)
        return
      }

      const progress = Math.min((now - start) / DURATION, 1)
      setOkProgress(progress)

      if (progress < 1) {
        okRafRef.current = requestAnimationFrame(tick)
      } else {
        okRafRef.current = null
        const el = document.elementFromPoint(startX, startY)
        if (el) el.click()
        setOkPending(null)
        setOkProgress(0)
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

    // 메뉴 화면 좌우 스와이프 → 페이지/탭 전환
    if (currentScreen === 'menu' && (gesture === 'swipe_left' || gesture === 'swipe_right')) {
      menuSwipeRef.current?.(gesture === 'swipe_left' ? 'left' : 'right')
      showLabel(GESTURE_LABELS[gesture])
      return
    }

    if (gesture.startsWith('swipe_')) showLabel(GESTURE_LABELS[gesture])
  }, [showLabel, fireOk, scrollAtPointer])

  useGesture({ onPointer: handlePointer, onGesture: handleGesture, enabled: true })

  const nav = (s) => setScreen(s)

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

  const screens = {
    start:       <StartScreen {...props} />,
    orderType:   <OrderTypeScreen nav={nav} setOrderType={setOrderType} />,
    menu:        <MenuScreen {...props} swipeRef={menuSwipeRef} />,
    cart:        <CartScreen {...props} />,
    payment:     <PaymentScreen {...props} />,
    complete:    <CompletionScreen orderNum={orderNum} nav={nav} />,
    cardPayment: <CardPaymentScreen {...props} />,
    payPayment:  <PayPaymentScreen {...props} />,
    cashPayment: <CashPaymentScreen {...props} />,
  }

  return (
    <LocaleProvider>
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

        {/* ── 제스처 포인터 ── */}
        {pointer && (
          <div style={{
            position: 'fixed',
            left: pointer.x - 14,
            top:  pointer.y - 14,
            width: 28, height: 28,
            borderRadius: '50%',
            background: 'rgba(255, 80, 80, 0.55)',
            border: '2.5px solid rgba(255,255,255,0.85)',
            pointerEvents: 'none',
            zIndex: 9000,
            transition: 'none',
          }} />
        )}

        {/* ── OK 로딩 링 (0.5초) ── */}
        {okPending && (
          <div style={{
            position: 'fixed',
            left: okPending.x - 28,
            top:  okPending.y - 28,
            width: 56, height: 56,
            borderRadius: '50%',
            background: `conic-gradient(
              rgba(80, 210, 255, 0.95) ${okProgress * 360}deg,
              rgba(255,255,255,0.18) 0deg
            )`,
            pointerEvents: 'none',
            zIndex: 9004,
          }}>
            {/* 안쪽 구멍 */}
            <div style={{
              position: 'absolute',
              inset: 7,
              borderRadius: '50%',
              background: 'rgba(0,0,0,0.55)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'rgba(255,255,255,0.9)',
              fontSize: 14, fontWeight: 700,
            }}>✓</div>
          </div>
        )}

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
    </LocaleProvider>
  )
}
