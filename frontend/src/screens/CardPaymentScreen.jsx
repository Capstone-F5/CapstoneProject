export function PaymentWaitScreen({ title, total, illustration, onCancel, onComplete }) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#fff',
      alignItems: 'center',
      padding: 'clamp(60px, 14vw, 80px) clamp(16px, 6vw, 32px) clamp(28px, 7vw, 44px)',
    }}>
      <div style={{ width: '100%', textAlign: 'center' }}>
        <div style={{
          fontSize: 'clamp(20px, 6vw, 24px)', fontWeight: 900,
          marginBottom: 'clamp(20px, 6vw, 32px)', lineHeight: 1.3,
        }}>
          {title}
        </div>

        {/* Amount box */}
        <div style={{
          background: '#616161', borderRadius: 8,
          padding: '16px 20px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: 'clamp(28px, 8vw, 48px)',
        }}>
          <span style={{ color: '#ccc', fontSize: 14 }}>결제할 금액</span>
          <span style={{ color: '#F5B800', fontSize: 'clamp(18px, 6vw, 24px)', fontWeight: 900 }}>
            {(total || 0).toLocaleString()}
          </span>
        </div>

        {illustration}
      </div>

      <div style={{ flex: 1 }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
        <button onClick={onCancel} style={{
          padding: '14px 40px', borderRadius: 12,
          border: 'none', background: '#d8d8d8', color: '#555',
          fontSize: 16, fontWeight: 700, cursor: 'pointer',
        }}>취소</button>
        {onComplete && (
          <button onClick={onComplete} style={{
            padding: '14px 40px', borderRadius: 12,
            border: 'none', background: '#d8d8d8', color: '#555',
            fontSize: 16, fontWeight: 700, cursor: 'pointer',
          }}>완료</button>
        )}
      </div>
    </div>
  )
}

function CardIllustration() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
      {/* Card reader */}
      <div style={{
        width: 72, height: 96, background: '#bdbdbd',
        borderRadius: 8, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'flex-start',
        paddingTop: 10, position: 'relative',
      }}>
        <div style={{ width: 36, height: 4, background: '#888', borderRadius: 2, marginBottom: 4 }} />
        <div style={{ fontSize: 8, color: '#fff', fontWeight: 700, letterSpacing: 0.5 }}>IC CARD</div>
        <div style={{ position: 'absolute', bottom: 28, width: 40, height: 4, background: '#555', borderRadius: 2 }} />
        <div style={{ position: 'absolute', bottom: 8, width: 24, height: 24, borderRadius: '50%', background: '#999' }} />
      </div>
      {/* Card + hand */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{
          width: 68, height: 44, borderRadius: 6,
          background: 'linear-gradient(135deg, #F5B800, #E6A700)',
          boxShadow: '0 3px 10px rgba(0,0,0,0.2)',
          position: 'relative', flexShrink: 0,
        }}>
          <div style={{
            position: 'absolute', left: 6, top: 8,
            width: 20, height: 14, borderRadius: 3,
            border: '1.5px solid rgba(255,255,255,0.6)',
          }} />
          <div style={{
            position: 'absolute', right: 6, bottom: 8,
            display: 'flex', gap: 3,
          }}>
            {[0,1,2,3].map(i => (
              <div key={i} style={{ width: 5, height: 5, borderRadius: '50%', background: 'rgba(255,255,255,0.5)' }} />
            ))}
          </div>
        </div>
        <div style={{ fontSize: 40, marginLeft: -4 }}>✋</div>
      </div>
    </div>
  )
}

export default function CardPaymentScreen({ total, clearCart, nav }) {
  return (
    <PaymentWaitScreen
      title="카드를 리더기에 읽혀주세요"
      total={total}
      illustration={<CardIllustration />}
      onCancel={() => nav('payment')}
      onComplete={() => { clearCart(); nav('start') }}
    />
  )
}
