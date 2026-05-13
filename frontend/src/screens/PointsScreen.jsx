import { useState } from 'react'

const KEYS = ['1','2','3','4','5','6','7','8','9','지움','0','010']

export default function PointsScreen({ nav }) {
  const [input, setInput] = useState('')

  const handleKey = (k) => {
    if (k === '지움') setInput(p => p.slice(0, -1))
    else if (k === '010') setInput('010')
    else if (input.length < 11) setInput(p => p + k)
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#fff',
      alignItems: 'center',
      padding: 'clamp(40px, 10vw, 56px) clamp(16px, 6vw, 28px) clamp(24px, 6vw, 36px)',
    }}>
      <div style={{ fontSize: 'clamp(22px, 7vw, 30px)', fontWeight: 900, marginBottom: 32 }}>
        F BURGER 포인트
      </div>
      <div style={{ fontSize: 'clamp(14px, 4vw, 17px)', color: '#444', marginBottom: 16, alignSelf: 'stretch', textAlign: 'center' }}>
        휴대폰 번호를 입력해주세요.
      </div>

      {/* Input */}
      <div style={{
        width: '100%', border: '2.5px solid #f00', borderRadius: 8,
        padding: 'clamp(12px, 3vw, 16px) 18px',
        fontSize: 'clamp(18px, 5vw, 22px)', fontWeight: 700, color: '#1a1a1a',
        minHeight: 54, marginBottom: 24, letterSpacing: 3,
      }}>
        {input || ' '}
      </div>

      {/* Keypad */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 'clamp(6px, 2vw, 10px)', width: '100%', marginBottom: 'auto',
      }}>
        {KEYS.map(k => (
          <button key={k} onClick={() => handleKey(k)} style={{
            padding: 'clamp(14px, 4vw, 19px) 0',
            background: '#9E9E9E', color: '#fff',
            border: 'none', borderRadius: 8,
            fontSize: 'clamp(16px, 5vw, 20px)', fontWeight: 700, cursor: 'pointer',
          }}>
            {k}
          </button>
        ))}
      </div>

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 16, width: '100%', marginTop: 24 }}>
        <button onClick={() => nav('cart')} style={{
          flex: 1, padding: '15px 0',
          border: 'none', borderRadius: 50,
          background: '#d4d4d4', color: '#555',
          fontSize: 'clamp(15px, 4.5vw, 18px)', fontWeight: 700, cursor: 'pointer',
        }}>취소</button>
        <button onClick={() => nav('payment')} style={{
          flex: 1, padding: '15px 0',
          border: 'none', borderRadius: 50,
          background: '#F5B800', color: '#1a1a1a',
          fontSize: 'clamp(15px, 4.5vw, 18px)', fontWeight: 700, cursor: 'pointer',
        }}>확인</button>
      </div>
    </div>
  )
}
