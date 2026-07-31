const NAV_ITEMS = [
  { key: 'dashboard', label: '대시보드' },
  { key: 'orders',    label: '주문 관리' },
  { key: 'payments',  label: '결제·환불' },
  { key: 'menu',      label: '메뉴 관리' },
  { key: 'coupons',   label: '쿠폰·할인' },
  { key: 'users',     label: '회원 관리' },
]

const PAGE_TITLES = {
  dashboard: '대시보드',
  orders:    '주문 관리',
  payments:  '결제·환불',
  menu:      '메뉴 관리',
  coupons:   '쿠폰·할인',
  users:     '회원 관리',
}

export default function Layout({ admin, currentPage, onNavigate, onLogout, children }) {
  return (
    <div className="admin-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <img src="/logo.png" alt="버거 로고" style={{ height: 44, objectFit: 'contain', display: 'block' }} />
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <div
              key={item.key}
              className={`sidebar-nav-item${currentPage === item.key ? ' active' : ''}`}
              onClick={() => onNavigate(item.key)}
            >
              {item.label}
            </div>
          ))}
        </nav>
      </aside>

      {/* Main */}
      <div className="admin-main">
        {/* Header */}
        <header className="admin-header">
          <h1 className="admin-header-title">{PAGE_TITLES[currentPage] ?? ''}</h1>
          <div className="admin-header-right">
            <span className="admin-header-user-label">사용자</span>
            <span className="admin-role-badge">{admin?.role ?? 'STAFF'}</span>
            <button className="btn-logout" onClick={onLogout}>로그아웃</button>
          </div>
        </header>

        {/* Content */}
        <main className="admin-content">
          {children}
        </main>
      </div>
    </div>
  )
}
