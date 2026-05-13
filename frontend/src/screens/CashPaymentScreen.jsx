import { PaymentWaitScreen } from './CardPaymentScreen'

function CashIllustration() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'relative' }}>
        <div style={{
          width: 90, height: 110, borderRadius: 10,
          background: '#bdbdbd',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', paddingTop: 14, gap: 6,
        }}>
          <div style={{ width: 50, height: 6, background: '#757575', borderRadius: 3 }} />
          <div style={{ width: 50, height: 3, background: '#9e9e9e', borderRadius: 2 }} />
          <div style={{ width: 50, height: 3, background: '#9e9e9e', borderRadius: 2 }} />
          <div style={{
            width: 60, height: 40,
            border: '2px solid #9e9e9e', borderRadius: 6,
            marginTop: 4, background: '#d0d0d0',
          }} />
        </div>
        <div style={{ position: 'absolute', bottom: 20, right: -52 }}>
          <div style={{
            width: 68, height: 34, borderRadius: 4,
            background: 'linear-gradient(135deg, #66BB6A, #43A047)',
            boxShadow: '1px 2px 6px rgba(0,0,0,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 4,
          }}>
            {[0,1].map(i => (
              <div key={i} style={{
                width: 14, height: 14, borderRadius: '50%',
                border: '1.5px solid rgba(255,255,255,0.5)',
              }} />
            ))}
          </div>
          <div style={{ fontSize: 28, textAlign: 'center', marginTop: 2 }}>✋</div>
        </div>
      </div>
    </div>
  )
}

export default function CashPaymentScreen({ total, nav }) {
  return (
    <PaymentWaitScreen
      title="현금을 투입해주세요"
      total={total}
      illustration={<CashIllustration />}
      onCancel={() => nav('payment')}
    />
  )
}
