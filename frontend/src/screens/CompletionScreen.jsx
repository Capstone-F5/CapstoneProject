import Logo from '../components/Logo'

export default function CompletionScreen({ orderNum, nav }) {
  const numStr = String(orderNum ?? 0).padStart(3, '0')

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#f5f5f5',
    }}>
      {/* 헤더 */}
      <div style={{
        background: '#744032', padding: '10px 16px', flexShrink: 0,
        display: 'flex', justifyContent: 'center', alignItems: 'center',
      }}>
        <Logo height={38} />
      </div>

      {/* 본문 */}
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: 'clamp(32px,8vw,48px) clamp(20px,6vw,32px)',
        gap: 'clamp(24px,6vw,36px)',
      }}>
        <div style={{ fontSize: 'clamp(22px,6vw,28px)', fontWeight: 900, color: '#1a1a1a' }}>
          결제가 완료되었습니다.
        </div>

        {/* 주문번호 카드 */}
        <div style={{
          border: '3px solid #e00', borderRadius: 20,
          background: '#fff', textAlign: 'center',
          padding: 'clamp(32px,8vw,52px) clamp(48px,12vw,80px)',
          boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
        }}>
          <div style={{ fontSize: 'clamp(15px,4vw,18px)', fontWeight: 600, color: '#555', marginBottom: 16 }}>
            주문번호
          </div>
          <div style={{ lineHeight: 1 }}>
            <span style={{ fontSize: 'clamp(56px,15vw,80px)', fontWeight: 900, color: '#e00' }}>
              {numStr}
            </span>
            <span style={{ fontSize: 'clamp(24px,6vw,32px)', fontWeight: 700, color: '#e00', marginLeft: 4 }}>
              번
            </span>
          </div>
        </div>

        <div style={{ fontSize: 'clamp(15px,4vw,18px)', color: '#666', fontWeight: 500 }}>
          이용해 주셔서 감사합니다.
        </div>
      </div>

      {/* 하단 버튼 */}
      <div style={{
        padding: 'clamp(16px,4vw,20px) clamp(20px,6vw,32px) clamp(24px,6vw,36px)',
        display: 'flex', gap: 14, flexShrink: 0,
      }}>
        <button onClick={() => nav('start')} style={{
          flex: 1, padding: 'clamp(16px,4vw,22px) 0',
          border: '2px solid #744032', borderRadius: 16,
          background: '#fff', color: '#744032',
          fontSize: 'clamp(15px,4vw,18px)', fontWeight: 700, cursor: 'pointer',
          boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        }}>영수증 받기</button>
        <button onClick={() => nav('start')} style={{
          flex: 1, padding: 'clamp(16px,4vw,22px) 0',
          border: 'none', borderRadius: 16,
          background: '#F5B800', color: '#1a1a1a',
          fontSize: 'clamp(15px,4vw,18px)', fontWeight: 700, cursor: 'pointer',
          boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        }}>주문번호만 받기</button>
      </div>
    </div>
  )
}
