export default function StartScreen({ nav }) {
  return (
    <div
      onClick={() => nav('orderType')}
      style={{
        flex: 1,
        minHeight: '100dvh',
        minHeight: '100vh',
        backgroundImage: "url('/bg.jpg')",
        backgroundSize: 'cover',
        backgroundPosition: 'center center',
        backgroundRepeat: 'no-repeat',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '0 24px 52px',
        cursor: 'pointer',
        userSelect: 'none',
        position: 'relative',
      }}
    >
      <button
        onClick={(e) => { e.stopPropagation(); nav('orderType') }}
        style={{
          width: '100%',
          maxWidth: 320,
          padding: '18px 0',
          background: '#fff',
          color: '#744032',
          border: 'none',
          borderRadius: 50,
          fontSize: 20,
          fontWeight: 900,
          boxShadow: '0 4px 24px rgba(0,0,0,0.22)',
          marginBottom: 28,
        }}
      >
        주문 시작하기
      </button>

      <div style={{ display: 'flex', gap: 24 }}>
        {['한글', 'English', '中文', '日本語'].map((lang, i) => (
          <button
            key={lang}
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'none',
              border: 'none',
              color: i === 0 ? '#fff' : 'rgba(255,255,255,0.55)',
              fontSize: 13,
              fontWeight: i === 0 ? 700 : 400,
              cursor: 'pointer',
              padding: '4px 0',
            }}
          >
            {lang}
          </button>
        ))}
      </div>
    </div>
  )
}
