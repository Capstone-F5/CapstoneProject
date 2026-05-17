import { useState } from 'react'
import { LocaleProvider } from './i18n/LocaleContext'
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

export default function App() {
  const [screen,    setScreen]    = useState('start')
  const [cart,      setCart]      = useState([])
  const [orderType, setOrderType] = useState(null)
  const [orderNum,  setOrderNum]  = useState(null)
  const [chatOpen,  setChatOpen]  = useState(false)

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
    menu:        <MenuScreen {...props} />,
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
      </>
    </LocaleProvider>
  )
}
