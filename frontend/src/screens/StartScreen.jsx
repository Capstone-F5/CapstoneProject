import { useEffect } from 'react'
import { useLocale } from '../i18n/LocaleContext'
import useT from '../i18n/useT'
import IdleOverlay from '../components/IdleOverlay'

const LANGS = [
  { code: 'ko', label: '한글' },
  { code: 'en', label: 'English' },
  { code: 'zh', label: '中文' },
  { code: 'ja', label: '日本語' },
]

export default function StartScreen({
  nav,
  gestureEnabled, setGestureEnabled,
  pipEnabled,     setPipEnabled,
}) {
  const { locale, setLocale } = useLocale()
  const t = useT()

  useEffect(() => { setLocale('ko') }, [])

  // 작은 토글 버튼 스타일
  const toggleBtn = (active, disabled = false) => ({
    padding: '8px 14px',
    background: disabled
      ? 'rgba(255,255,255,0.18)'
      : active ? 'rgba(80,200,140,0.92)' : 'rgba(40,40,40,0.78)',
    color: disabled ? 'rgba(255,255,255,0.55)' : '#fff',
    border: '1.5px solid rgba(255,255,255,0.55)',
    borderRadius: 22,
    fontSize: 13,
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    textShadow: '0 1px 2px rgba(0,0,0,0.6)',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    display: 'flex', alignItems: 'center', gap: 6,
    transition: 'background 0.18s',
  })

  const dot = (on) => (
    <span style={{
      width: 8, height: 8, borderRadius: '50%',
      background: on ? '#7fff9f' : 'rgba(255,255,255,0.4)',
      boxShadow: on ? '0 0 6px #7fff9f' : 'none',
    }} />
  )

  return (
    <>
    <div
      onClick={() => nav('orderType')}
      style={{
        height: '100%',
        backgroundImage: "url('/bg.png')",
        backgroundSize: 'cover',
        backgroundPosition: 'center center',
        backgroundRepeat: 'no-repeat',
        overflow: 'hidden',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '0 36px 78px',
      }}
    >
      {/* 설정 토글 — 좌측 상단 */}
      {setGestureEnabled && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            position: 'absolute',
            top: 16, left: 16,
            display: 'flex', gap: 8,
            zIndex: 10,
          }}
        >
          <button
            onClick={() => setGestureEnabled(v => !v)}
            style={toggleBtn(gestureEnabled)}
            title="손동작 인식 켜기/끄기"
          >
            {dot(gestureEnabled)} 손동작 {gestureEnabled ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={() => gestureEnabled && setPipEnabled(v => !v)}
            disabled={!gestureEnabled}
            style={toggleBtn(pipEnabled && gestureEnabled, !gestureEnabled)}
            title="카메라 미리보기 켜기/끄기"
          >
            {dot(pipEnabled && gestureEnabled)} 카메라 {pipEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
      )}

      {/* 주문 시작 버튼 */}
      <button
        onClick={e => { e.stopPropagation(); nav('orderType') }}
        style={{
          width: '100%',
          maxWidth: 480,
          padding: '19px 0',
          background: '#fff',
          color: '#1a1a1a',
          border: 'none',
          borderRadius: 50,
          fontSize: 39,
          fontWeight: 900,
          boxShadow: '0 8px 32px rgba(0,0,0,0.35), 0 2px 8px rgba(0,0,0,0.20)',
          marginBottom: 42,
          cursor: 'pointer',
        }}
      >
        {t('startOrder')}
      </button>

      {/* 언어 선택 */}
      <div style={{ display: 'flex', gap: 36 }}>
        {LANGS.map(({ code, label }) => (
          <button
            key={code}
            onClick={e => { e.stopPropagation(); setLocale(code) }}
            style={{
              background: 'none',
              border: 'none',
              color: locale === code ? '#fff' : 'rgba(255,255,255,0.75)',
              fontSize: 20,
              fontWeight: locale === code ? 700 : 400,
              cursor: 'pointer',
              padding: '6px 0',
              textDecoration: locale === code ? 'underline' : 'none',
              textUnderlineOffset: 4,
              textShadow: locale === code
                ? '0 0 6px rgba(0,0,0,0.6), 1px 1px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000'
                : '1px 1px 3px rgba(0,0,0,0.8), -1px -1px 3px rgba(0,0,0,0.8)',
            }}
          >
            {label}
          </button>
        ))}
      </div>
    </div>

    {/* 대기 화면 idle 3분 → 언어·세션 초기화 (nav('start')에서 setLocale('ko') + sessionStorage 클리어) */}
    <IdleOverlay
      idleMs={180000}
      warningSeconds={0}
      onExpire={() => nav('start')}
    />
    </>
  )
}
