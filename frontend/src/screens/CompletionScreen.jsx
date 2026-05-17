import { useState, useEffect } from 'react'
import Logo from '../components/Logo'
import useT from '../i18n/useT'

const TOTAL_SECONDS = 10

export default function CompletionScreen({ orderNum, nav }) {
  const t = useT()
  const numStr = String(orderNum ?? 0).padStart(3, '0')
  const [timeLeft, setTimeLeft] = useState(TOTAL_SECONDS)

  useEffect(() => {
    const interval = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) { clearInterval(interval); nav('start'); return 0 }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const r = 20
  const circumference = 2 * Math.PI * r
  const dashOffset = circumference * (1 - timeLeft / TOTAL_SECONDS)

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      height: '100%', background: '#f5f5f5',
    }}>
      {/* 헤더 */}
      <div style={{
        background: '#744032', padding: '16px 32px', flexShrink: 0,
        display: 'flex', justifyContent: 'center', alignItems: 'center',
      }}>
        <Logo height={64} />
      </div>

      {/* justify-content:center + overflow:auto 조합은 상단 클리핑 버그 발생
           → 스크롤 컨테이너와 margin:auto 내부 div로 분리하여 해결 */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        <div style={{
          margin: 'auto',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center',
          gap: 'clamp(14px, 3.5vw, 24px)',
          padding: 'clamp(16px, 4vw, 32px) clamp(24px, 8vw, 48px)',
          width: '100%', boxSizing: 'border-box',
        }}>
          <div style={{ fontSize: 'clamp(24px, 7vw, 38px)', fontWeight: 900, color: '#1a1a1a', textAlign: 'center' }}>
            {t('paymentComplete')}
          </div>

          {/* 주문번호 카드 */}
          <div style={{
            border: '4px solid #e00', borderRadius: 24,
            background: '#fff', textAlign: 'center',
            padding: 'clamp(16px, 5vw, 36px) clamp(32px, 10vw, 80px)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
          }}>
            <div style={{ fontSize: 'clamp(16px, 4.5vw, 24px)', fontWeight: 600, color: '#555', marginBottom: 10 }}>
              {t('orderNumber')}
            </div>
            <div style={{ lineHeight: 1 }}>
              <span style={{ fontSize: 'clamp(56px, 16vw, 100px)', fontWeight: 900, color: '#e00' }}>
                {numStr}
              </span>
              <span style={{ fontSize: 'clamp(24px, 7vw, 40px)', fontWeight: 700, color: '#e00', marginLeft: 6 }}>
                {t('orderUnit')}
              </span>
            </div>
          </div>

          <div style={{ fontSize: 'clamp(16px, 4.5vw, 24px)', color: '#666', fontWeight: 500, textAlign: 'center' }}>
            {t('thankYou')}
          </div>

          {/* 버튼 */}
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
            <button onClick={() => nav('start')} style={{
              width: 'clamp(130px, 28vw, 200px)',
              padding: 'clamp(14px, 3.5vw, 22px) 0',
              border: '2px solid #744032', borderRadius: 20,
              background: '#fff', color: '#744032',
              fontSize: 'clamp(15px, 4vw, 22px)', fontWeight: 700, cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
            }}>{t('getReceipt')}</button>
            <button onClick={() => nav('start')} style={{
              width: 'clamp(130px, 28vw, 200px)',
              padding: 'clamp(14px, 3.5vw, 22px) 0',
              border: 'none', borderRadius: 20,
              background: '#F5B800', color: '#1a1a1a',
              fontSize: 'clamp(15px, 4vw, 22px)', fontWeight: 700, cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
            }}>{t('getNumber')}</button>
          </div>

          {/* 자동 복귀 카운트다운 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#999', fontSize: 'clamp(12px, 3vw, 16px)' }}>
            <svg width={48} height={48} style={{ flexShrink: 0 }}>
              <circle cx={24} cy={24} r={r} fill="none" stroke="#e0e0e0" strokeWidth={4} />
              <circle cx={24} cy={24} r={r}
                fill="none" stroke="#744032" strokeWidth={4}
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
                transform="rotate(-90 24 24)"
                style={{ transition: 'stroke-dashoffset 0.9s linear' }}
              />
              <text x={24} y={29} textAnchor="middle" fontSize={14} fontWeight={900} fill="#744032">
                {timeLeft}
              </text>
            </svg>
            <span>{t('autoReturn', timeLeft)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
