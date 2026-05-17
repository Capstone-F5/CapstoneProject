export default function PaymentScreen({ total, nav }) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#fff', padding: 'clamp(32px, 8vw, 56px) clamp(16px, 6vw, 28px) 32px',
    }}>
      {/* Greeting */}
      <div style={{ marginBottom: 'clamp(24px, 6vw, 36px)' }}>
        <div style={{ fontSize: 'clamp(20px, 6vw, 26px)', fontWeight: 900, color: '#1a1a1a', lineHeight: 1.45 }}>
          안녕하세요, OOO 님
        </div>
        <div style={{ fontSize: 'clamp(20px, 6vw, 26px)', fontWeight: 900, color: '#1a1a1a' }}>
          결제 수단을 선택하세요.
        </div>
      </div>

      {/* Card / Cash row */}
      <div style={{ display: 'flex', borderBottom: '1px solid #eee', marginBottom: 24 }}>
        <button onClick={() => nav('cardPayment')} style={{
          flex: 1, padding: '20px 12px',
          border: 'none', background: 'none',
          borderRight: '1px solid #eee',
          display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 12,
          cursor: 'pointer',
        }}>
          <div style={{ fontSize: 12, color: '#888', fontWeight: 600 }}>신용카드/삼성페이</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <PayBadge bg="linear-gradient(135deg,#1565C0,#42A5F5)" color="#fff">💳</PayBadge>
            <PayBadge bg="#1428A0" color="#fff" small>
              <span style={{ fontSize: 8, fontWeight: 900, display: 'block', lineHeight: 1 }}>SAMSUNG</span>
              <span style={{ fontSize: 11, fontWeight: 900 }}>Pay</span>
            </PayBadge>
          </div>
        </button>

        <button onClick={() => nav('cashPayment')} style={{
          flex: 1, padding: '20px 12px',
          border: 'none', background: 'none',
          display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 12,
          cursor: 'pointer',
        }}>
          <div style={{ fontSize: 12, color: '#888', fontWeight: 600 }}>현금</div>
          <PayBadge bg="#E8F5E9" color="#333">💵</PayBadge>
        </button>
      </div>

      {/* Easy Pay */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: '#888', fontWeight: 600, marginBottom: 12 }}>간편결제</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            { color: '#03C75A', text: 'N pay',   sub: '네이버페이' },
            { color: '#FEE500', text: '• pay',   sub: '카카오페이', tc: '#333' },
            { color: '#1E1E1E', text: 'zeroPay', sub: '제로페이'   },
            { color: '#FF0000', text: 'PAYCO',   sub: '페이코'     },
          ].map(p => (
            <button key={p.sub} onClick={() => nav('payPayment')} style={{
              border: '1.5px solid #ebebeb', borderRadius: 12,
              background: '#fff', padding: '18px 12px',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
              cursor: 'pointer',
            }}>
              <div style={{ fontSize: 15, fontWeight: 900, color: p.color }}>{p.text}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{p.sub}</div>
            </button>
          ))}
        </div>
      </div>

      <button onClick={() => nav('cart')} style={{
        width: '100%', padding: '15px 0', marginTop: 24,
        border: '1px solid #ccc', borderRadius: 12,
        background: '#e8e8e8', color: '#666',
        fontSize: 16, fontWeight: 700, cursor: 'pointer',
        flexShrink: 0,
      }}>취소</button>
    </div>
  )
}

function PayBadge({ bg, color, small, children }) {
  return (
    <div style={{
      width: 54, height: 36, borderRadius: 6,
      background: bg,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      color, fontSize: small ? undefined : 18,
    }}>
      {children}
    </div>
  )
}
