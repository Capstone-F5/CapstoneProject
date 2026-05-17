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
        if (prev <= 1) {
          clearInterval(interval)
          nav('start')
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const progress = timeLeft / TOTAL_SECONDS // 1.0 → 0.0
  const circumference = 2 * Math.PI * 24   // r=24
  const dashOffset = circumference * (1 - progress)

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#f5f5f5',
    }}>
      {/* 헤더 */}
      <div style={{
        background: '#744032', padding: '20px 32px', flexShrink: 0,
        display: 'flex', justifyContent: 'center', alignItems: 'center',
      }}>
        <Logo height={76} />
      </div>

      {/* 본문 + 버튼 */}
      <div style={{ flex: 1, position: 'relative' }}>

        {/* 중앙 콘텐츠 */}
        <div style={{
          position: 'absolute', inset: 0,
          bottom: '30%',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          gap: 'clamp(24px,6vw,36px)',
          padding: '0 clamp(30px,9vw,48px)',
        }}>
          <div style={{ fontSize: 'clamp(33px,9vw,42px)', fontWeight: 900, color: '#1a1a1a' }}>
            {t('paymentComplete')}
          </div>

          {/* 주문번호 카드 */}
          <div style={{
            border: '4px solid #e00', borderRadius: 30,
            background: '#fff', textAlign: 'center',
            padding: 'clamp(28px,7vw,44px) clamp(56px,14vw,100px)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
          }}>
            <div style={{ fontSize: 'clamp(22px,6vw,27px)', fontWeight: 600, color: '#555', marginBottom: 16 }}>
              {t('orderNumber')}
            </div>
            <div style={{ lineHeight: 1 }}>
              <span style={{ fontSize: 'clamp(84px,22vw,120px)', fontWeight: 900, color: '#e00' }}>
                {numStr}
              </span>
              <span style={{ fontSize: 'clamp(36px,9vw,48px)', fontWeight: 700, color: '#e00', marginLeft: 6 }}>
                {t('orderUnit')}
              </span>
            </div>
          </div>

          <div style={{ fontSize: 'clamp(22px,6vw,27px)', color: '#666', fontWeight: 500 }}>
            {t('thankYou')}
          </div>
        </div>

        {/* 버튼 영역 */}
        <div style={{
          position: 'absolute',
          bottom: '30%',
          left: 0, right: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', gap: 20,
          padding: '0 clamp(30px,9vw,48px)',
        }}>
          <div style={{ display: 'flex', gap: 20 }}>
            <button onClick={() => nav('start')} style={{
              width: 'clamp(160px,36vw,240px)',
              padding: 'clamp(20px,5vw,28px) 0',
              border: '2px solid #744032', borderRadius: 24,
              background: '#fff', color: '#744032',
              fontSize: 'clamp(20px,5.5vw,26px)', fontWeight: 700, cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
            }}>{t('getReceipt')}</button>
            <button onClick={() => nav('start')} style={{
              width: 'clamp(160px,36vw,240px)',
              padding: 'clamp(20px,5vw,28px) 0',
              border: 'none', borderRadius: 24,
              background: '#F5B800', color: '#1a1a1a',
              fontSize: 'clamp(20px,5.5vw,26px)', fontWeight: 700, cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
            }}>{t('getNumber')}</button>
          </div>

          {/* 자동 복귀 카운트다운 */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            color: '#999', fontSize: 'clamp(14px,3.8vw,17px)',
          }}>
            {/* SVG 원형 진행바 */}
            <svg width={56} height={56} style={{ flexShrink: 0 }}>
              {/* 배경 원 */}
              <circle cx={28} cy={28} r={24}
                fill="none" stroke="#e0e0e0" strokeWidth={4} />
              {/* 진행 원 */}
              <circle cx={28} cy={28} r={24}
                fill="none" stroke="#744032" strokeWidth={4}
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
                transform="rotate(-90 28 28)"
                style={{ transition: 'stroke-dashoffset 0.9s linear' }}
              />
              <text x={28} y={33} textAnchor="middle"
                fontSize={16} fontWeight={900} fill="#744032">
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
