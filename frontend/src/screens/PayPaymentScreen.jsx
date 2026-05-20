import { PaymentWaitScreen } from './CardPaymentScreen'

function BarcodeIllustration() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 24 }}>
      <div style={{ position: 'relative' }}>
        <div style={{
          width: 72, height: 110, borderRadius: 10,
          border: '3px solid #bbb', background: '#f5f5f5',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          padding: 8, overflow: 'hidden',
        }}>
          <div style={{ fontSize: 8, color: '#aaa', marginBottom: 4 }}>10:00</div>
          <div style={{ display: 'flex', gap: 1, alignItems: 'flex-end', height: 40 }}>
            {[3,5,2,4,3,5,2,4,3,5,2,4,3,5,2,4].map((h, i) => (
              <div key={i} style={{ width: 2, height: h * 6, background: '#222' }} />
            ))}
          </div>
          <div style={{ fontSize: 7, color: '#555', marginTop: 3, letterSpacing: 0.5 }}>1234567890</div>
          <div style={{
            position: 'absolute', left: 8, right: 8, top: '52%',
            height: 1.5, background: '#f00', opacity: 0.8,
          }} />
        </div>
        <div style={{ textAlign: 'center', fontSize: 30, marginTop: -4 }}>✊</div>
      </div>

      <div style={{
        width: 64, height: 64, borderRadius: 8,
        background: '#424242',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          width: 24, height: 24, borderRadius: '50%',
          background: '#ef5350',
          boxShadow: '0 0 8px rgba(239,83,80,0.6)',
        }} />
      </div>
    </div>
  )
}

export default function PayPaymentScreen({ total, nav }) {
  return (
    <PaymentWaitScreen
      title="바코드를 스캔해 주세요"
      total={total}
      illustration={<BarcodeIllustration />}
      onCancel={() => nav('payment')}
    />
  )
}
