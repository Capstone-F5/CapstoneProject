import { useIdleTimer } from '../hooks/useIdleTimer'
import useT from '../i18n/useT'

// 90초 = 80초 대기 + 10초 카운트다운
export default function IdleOverlay({ onExpire, idleMs = 80000, warningSeconds = 10 }) {
  const secondsLeft = useIdleTimer({ idleMs, warningSeconds, onExpire })
  const t = useT()

  if (secondsLeft === null) return null

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.78)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 28,
    }}>
      {/* 카운트다운 링 */}
      <div style={{
        width: 140, height: 140, borderRadius: '50%',
        border: '6px solid #F5B800',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: '0 0 40px rgba(245,184,0,0.35)',
      }}>
        <span style={{ fontSize: 72, fontWeight: 900, color: '#fff', lineHeight: 1 }}>
          {secondsLeft}
        </span>
      </div>

      <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', textAlign: 'center', lineHeight: 1.5 }}>
        {t('autoReturn', secondsLeft)}
      </div>

      <div style={{ fontSize: 16, color: 'rgba(255,255,255,0.55)' }}>
        {t('idleTap')}
      </div>
    </div>
  )
}
