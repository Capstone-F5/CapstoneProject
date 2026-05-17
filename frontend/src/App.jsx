import { useState } from 'react'
import StartScreen from './screens/StartScreen'
import OrderTypeScreen from './screens/OrderTypeScreen'
import MenuScreen from './screens/MenuScreen'
import CartScreen from './screens/CartScreen'
import PaymentScreen from './screens/PaymentScreen'
import CompletionScreen from './screens/CompletionScreen'
import CardPaymentScreen from './screens/CardPaymentScreen'
import PayPaymentScreen from './screens/PayPaymentScreen'
import CashPaymentScreen from './screens/CashPaymentScreen'

export default function App() {
  const [screen,    setScreen]    = useState('start')
  const [cart,      setCart]      = useState([])
  const [orderType, setOrderType] = useState(null)
  const [orderNum,  setOrderNum]  = useState(null)

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
  const props = { cart, total, addToCart, updateQty, clearCart, nav, setOrderNum, orderType }

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
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>
      {screens[screen] ?? screens.start}
    </div>
  )
}
