import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

const isAdminRoute =
  window.location.pathname === '/admin' ||
  window.location.pathname.startsWith('/admin/')

const root = createRoot(document.getElementById('root'))

if (isAdminRoute) {
  document.title = 'F BURGER 관리자'
  Promise.all([
    import('./admin/AdminApp.jsx'),
    import('./admin/admin.css'),
  ]).then(([{ default: AdminApp }]) => {
    root.render(
      <StrictMode>
        <AdminApp />
      </StrictMode>,
    )
  })
} else {
  Promise.all([
    import('./App.jsx'),
    import('./index.css'),
  ]).then(([{ default: App }]) => {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  })
}
