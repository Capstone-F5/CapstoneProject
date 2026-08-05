import React from 'react'
import ReactDOM from 'react-dom/client'
import AdminApp from './admin/AdminApp.jsx'
import './admin/admin.css'

ReactDOM.createRoot(document.getElementById('admin-root')).render(
  <React.StrictMode>
    <AdminApp />
  </React.StrictMode>
)
