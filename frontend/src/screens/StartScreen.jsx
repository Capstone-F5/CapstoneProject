import { useEffect } from 'react'
import { useLocale } from '../i18n/LocaleContext'
import useT from '../i18n/useT'

const LANGS = [
  { code: 'ko', label: '한글' },
  { code: 'en', label: 'English' },
  { code: 'zh', label: '中文' },
  { code: 'ja', label: '日本語' },
]

export default function StartScreen({ nav }) {
  const { locale, setLocale } = useLocale()
  const t = useT()

  useEffect(() => { setLocale('ko') }, [])

  return (
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
  )
}
