import { useEffect, useState } from 'react'
import { useLocale } from '../i18n/LocaleContext'
import useT from '../i18n/useT'
import IdleOverlay from '../components/IdleOverlay'
import { fetchStartScreenImages } from '../services/settingsService'

const LANGS = [
  { code: 'ko', label: '한글' },
  { code: 'en', label: 'English' },
  { code: 'zh', label: '中文' },
  { code: 'ja', label: '日本語' },
]

// 대기화면 배경 — DB(GET /api/settings/start-screen-images)에서 받아온 목록을 5초 간격으로
// 부드럽게 크로스페이드 순환한다. 관리자가 나중에 이미지를 교체/추가하면 코드 수정 없이 반영된다.
// 한 장뿐이면 그냥 고정 배경으로 표시되고 순환 타이머 자체가 돌지 않는다.
const BG_INTERVAL_MS = 5000
const BG_FADE_MS = 1200

export default function StartScreen({ nav }) {
  const { locale, setLocale } = useLocale()
  const t = useT()
  const [bgImages, setBgImages] = useState(['/bg.png'])
  const [bgIndex, setBgIndex] = useState(0)

  useEffect(() => { setLocale('ko') }, [])

  useEffect(() => {
    let cancelled = false
    fetchStartScreenImages().then(urls => { if (!cancelled) setBgImages(urls) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    setBgIndex(0)
    if (bgImages.length < 2) return
    const timer = setInterval(() => {
      setBgIndex(i => (i + 1) % bgImages.length)
    }, BG_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [bgImages])

  return (
    <>
    <div
      onClick={() => nav('orderType')}
      style={{
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        userSelect: 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '0 36px 78px',
      }}
    >
      {/* 배경 이미지 크로스페이드 스택 */}
      {bgImages.map((src, i) => (
        <div
          key={src}
          style={{
            position: 'absolute', inset: 0,
            backgroundImage: `url('${src}')`,
            backgroundSize: 'cover',
            backgroundPosition: 'center center',
            backgroundRepeat: 'no-repeat',
            opacity: i === bgIndex ? 1 : 0,
            transition: `opacity ${BG_FADE_MS}ms ease-in-out`,
          }}
        />
      ))}

      {/* 회원가입 — 주문 흐름과 완전히 분리된 별도 화면으로 이동. 눈에 띄지 않게 우측 상단에 배치 */}
      <button
        onClick={e => { e.stopPropagation(); nav('signup') }}
        style={{
          position: 'absolute', top: 20, right: 20, zIndex: 1,
          background: 'rgba(0,0,0,0.35)',
          border: '1.5px solid rgba(255,255,255,0.6)',
          borderRadius: 20,
          color: '#fff',
          fontSize: 15,
          fontWeight: 700,
          padding: '9px 18px',
          cursor: 'pointer',
        }}
      >
        회원가입
      </button>

      {/* 주문 시작 버튼 */}
      <button
        onClick={e => { e.stopPropagation(); nav('orderType') }}
        style={{
          position: 'relative',
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
      <div style={{ position: 'relative', display: 'flex', gap: 36 }}>
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
