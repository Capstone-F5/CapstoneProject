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

  return (
    <div
      onClick={() => nav('orderType')}
      style={{
        flex: 1,
        minHeight: '100dvh',
        minHeight: '100vh',
        backgroundImage: "url('/bg.png')",
        backgroundSize: 'cover',
        backgroundPosition: 'center center',
        backgroundRepeat: 'no-repeat',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '0 36px 78px',
        cursor: 'pointer',
        userSelect: 'none',
        position: 'relative',
      }}
    >
      <button
        onClick={(e) => { e.stopPropagation(); nav('orderType') }}
        style={{
          width: '100%',
          maxWidth: 480,
          padding: '27px 0',
          background: '#fff',
          color: '#744032',
          border: 'none',
          borderRadius: 50,
          fontSize: 30,
          fontWeight: 900,
          boxShadow: '0 4px 24px rgba(0,0,0,0.22)',
          marginBottom: 42,
        }}
      >
        {t('startOrder')}
      </button>

      <div style={{ display: 'flex', gap: 36 }}>
        {LANGS.map(({ code, label }) => (
          <button
            key={code}
            onClick={(e) => { e.stopPropagation(); setLocale(code) }}
            style={{
              background: 'none',
              border: 'none',
              color: locale === code ? '#fff' : 'rgba(255,255,255,0.55)',
              fontSize: 20,
              fontWeight: locale === code ? 700 : 400,
              cursor: 'pointer',
              padding: '6px 0',
              textDecoration: locale === code ? 'underline' : 'none',
              textUnderlineOffset: 4,
            }}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
