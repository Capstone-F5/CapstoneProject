import { useState, useEffect } from 'react'
import { login, getMe, logout } from './api/adminApi.js'
import Layout from './components/Layout.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import PaymentsPage from './pages/PaymentsPage.jsx'
import MenuPage from './pages/MenuPage.jsx'
import CouponsPage from './pages/CouponsPage.jsx'
import UsersPage from './pages/UsersPage.jsx'

const PAGES = {
  dashboard: { label: '대시보드',  Component: DashboardPage },
  orders:    { label: '주문 관리', Component: OrdersPage    },
  payments:  { label: '결제·환불', Component: PaymentsPage  },
  menu:      { label: '메뉴 관리', Component: MenuPage      },
  coupons:   { label: '쿠폰·할인', Component: CouponsPage   },
  users:     { label: '회원 관리', Component: UsersPage     },
}

export default function AdminApp() {
  const [admin, setAdmin] = useState(null)
  const [page, setPage] = useState('dashboard')
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('admin_token')
    if (!token) { setChecking(false); return }
    getMe()
      .then(me => setAdmin(me))
      .catch(() => localStorage.removeItem('admin_token'))
      .finally(() => setChecking(false))
  }, [])

  const handleLogin = async (username, password) => {
    const data = await login(username, password)
    localStorage.setItem('admin_token', data.access_token)
    const me = await getMe()
    setAdmin(me)
  }

  const handleLogout = async () => {
    await logout()
    setAdmin(null)
    setPage('dashboard')
  }

  if (checking) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh', color:'#aaa', fontFamily:'Pretendard,sans-serif' }}>
        로딩 중…
      </div>
    )
  }

  if (!admin) {
    return <LoginPage onLogin={handleLogin} />
  }

  const PageComponent = PAGES[page]?.Component ?? DashboardPage

  return (
    <Layout
      admin={admin}
      currentPage={page}
      pages={PAGES}
      onNavigate={setPage}
      onLogout={handleLogout}
    >
      <PageComponent />
    </Layout>
  )
}
