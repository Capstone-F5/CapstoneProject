import { useState } from 'react'
import Logo from '../components/Logo'
import { registerCustomer } from '../services/pointsService'
import IdleOverlay from '../components/IdleOverlay'

// 주문 흐름과 완전히 분리된 별도 회원가입 화면. 전화번호를 결제 중 한 번 입력한다고
// 회원가입이 되는 게 아니므로, 정식 가입은 반드시 이 화면(POST /api/user/register)을 거친다.
const PHONE_KEYS = ['1','2','3','4','5','6','7','8','9','지움','0','010']

export default function SignupScreen({ nav }) {
  const [phoneInput, setPhoneInput] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)  // { alreadyMember } | null

  const handleKey = (key) => {
    if (key === '지움')                setPhoneInput(p => p.slice(0, -1))
    else if (key === '010')            setPhoneInput('010')
    else if (phoneInput.length < 11)   setPhoneInput(p => p + key)
    setError('')
  }

  const formatPhone = (v) => {
    const d = v.replace(/\D/g, '').slice(0, 11)
    if (d.length <= 3) return d
    if (d.length <= 7) return `${d.slice(0,3)}-${d.slice(3)}`
    return `${d.slice(0,3)}-${d.slice(3,7)}-${d.slice(7)}`
  }

  const handleSubmit = async () => {
    const digits = phoneInput.replace(/\D/g, '')
    if (digits.length !== 11) { setError('휴대폰 번호 11자리를 입력해 주세요'); return }
    setSubmitting(true)
    setError('')
    try {
      const res = await registerCustomer(digits, name.trim())
      setResult({ alreadyMember: res.alreadyMember })
    } catch (e) {
      setError(e.message || '회원가입에 실패했습니다')
    } finally {
      setSubmitting(false)
    }
  }

  const reset = () => {
    setPhoneInput(''); setName(''); setError(''); setResult(null)
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      height: '100%', background: '#f2f2f2', overflow: 'hidden',
    }}>
      {/* 헤더 */}
      <div style={{
        background: '#744032', padding: '20px 32px',
        display: 'flex', alignItems: 'center', flexShrink: 0,
      }}>
        <button onClick={() => nav('start')} style={{
          background: 'none', border: 'none',
          color: '#F5B800', fontSize: 60, lineHeight: 1,
          padding: '0 16px 0 0', cursor: 'pointer',
        }}>‹</button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <Logo height={76} />
        </div>
        <div style={{ width: 80 }} />
      </div>

      <div style={{
        flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column',
        alignItems: 'center', padding: '32px 24px', gap: 20,
      }}>
        {result ? (
          <div style={{
            width: '100%', maxWidth: 420, background: '#fff', borderRadius: 18,
            padding: '40px 28px', textAlign: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>{result.alreadyMember ? 'ℹ️' : '🎉'}</div>
            <p style={{ fontSize: 20, fontWeight: 900, marginBottom: 8 }}>
              {result.alreadyMember ? '이미 가입된 회원입니다' : '회원가입이 완료되었습니다'}
            </p>
            <p style={{ fontSize: 15, color: '#888', marginBottom: 28 }}>
              {formatPhone(phoneInput)}
            </p>
            <div style={{ display: 'flex', gap: 12 }}>
              <button onClick={reset} style={{
                flex: 1, padding: '16px 0', border: '1.5px solid #ddd', borderRadius: 12,
                background: '#fff', color: '#555', fontSize: 16, fontWeight: 700, cursor: 'pointer',
              }}>다른 번호로 가입</button>
              <button onClick={() => nav('start')} style={{
                flex: 1, padding: '16px 0', border: 'none', borderRadius: 12,
                background: '#F5B800', color: '#1a1a1a', fontSize: 16, fontWeight: 900, cursor: 'pointer',
              }}>처음으로</button>
            </div>
          </div>
        ) : (
          <>
            <p style={{ fontSize: 24, fontWeight: 900, color: '#1a1a1a' }}>회원가입</p>
            <p style={{ fontSize: 15, color: '#888', marginTop: -12, textAlign: 'center' }}>
              휴대폰 번호로 가입하면 주문 시 포인트를 적립·조회할 수 있어요.
            </p>

            <div style={{
              width: '100%', maxWidth: 420, border: '2px solid #e44', borderRadius: 10,
              padding: '14px', fontSize: 22, fontWeight: 700,
              minHeight: 58, textAlign: 'center', letterSpacing: 2, color: '#1a1a1a',
              background: '#fff',
            }}>
              {formatPhone(phoneInput) || '휴대폰 번호'}
            </div>

            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="이름 (선택)"
              style={{
                width: '100%', maxWidth: 420, boxSizing: 'border-box',
                border: '1.5px solid #e0e0e0', borderRadius: 10,
                padding: '14px', fontSize: 16,
              }}
            />

            {error && (
              <p style={{ fontSize: 14, color: '#e44', fontWeight: 700, margin: 0 }}>{error}</p>
            )}

            <div style={{
              width: '100%', maxWidth: 420,
              display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10,
            }}>
              {PHONE_KEYS.map(k => (
                <button key={k} onClick={() => handleKey(k)} style={{
                  padding: '22px 0', background: '#9e9e9e', color: '#fff',
                  border: 'none', borderRadius: 8, fontSize: 20, fontWeight: 700, cursor: 'pointer',
                }}>{k}</button>
              ))}
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting}
              style={{
                width: '100%', maxWidth: 420, padding: '18px 0', border: 'none', borderRadius: 12,
                background: submitting ? '#ccc' : '#F5B800', color: '#1a1a1a',
                fontSize: 20, fontWeight: 900, cursor: submitting ? 'default' : 'pointer',
              }}
            >{submitting ? '처리 중…' : '가입하기'}</button>
          </>
        )}
      </div>

      <IdleOverlay onExpire={() => nav('start')} />
    </div>
  )
}
