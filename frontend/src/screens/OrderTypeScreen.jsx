import Logo from '../components/Logo'
import useT from '../i18n/useT'

const ORDER_TYPE_CARD_RATIO = '1 / 1'

export default function OrderTypeScreen({ nav, setOrderType }) {
  const t = useT()
  const select = (type) => {
    setOrderType(type)
    nav('menu')
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#f5f5f5',
      alignItems: 'center',
      justifyContent: 'flex-start',
      padding: 'clamp(24px, 6vw, 36px) clamp(20px, 6vw, 32px)',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute',
        top: '40%',
        transform: 'translateY(-50%)',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        <Logo height={72} />

        <div style={{
          fontSize: 'clamp(20px, 5.3vw, 23px)', fontWeight: 700,
          color: '#1a1a1a', textAlign: 'center',
          margin: 'clamp(30px, 7.5vw, 42px) 0',
        }}>
          {t('selectLocation')}
        </div>

        <div style={{
          display: 'flex',
          gap: 'clamp(10px, 2.8vw, 14px)',
          width: '70%',
        }}>
          <TypeCard
            label={t('dineIn')}
            onClick={() => select('dine-in')}
          >
            <img
              src="/images/sets/F버거 세트.png"
              alt="dine-in"
              style={{ width: '70%', aspectRatio: '1 / 1', objectFit: 'scale-down' }}
            />
          </TypeCard>

          <TypeCard
            label={t('takeout')}
            onClick={() => select('takeout')}
          >
            <img
              src="/images/etc/Takeout.png"
              alt="포장"
              style={{ width: '70%', aspectRatio: '1 / 1', objectFit: 'scale-down' }}
            />

          </TypeCard>
        </div>
      </div>
    </div>
  )
}

function TypeCard({ label, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1, background: '#fff', border: 'none',
        borderRadius: 16, overflow: 'hidden', cursor: 'pointer',
        boxShadow: '0 2px 14px rgba(0,0,0,0.1)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', padding: 0,
        aspectRatio: ORDER_TYPE_CARD_RATIO,
      }}
    >
      <div style={{
        flex: 1,
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {children}
      </div>
      <div style={{
        padding: 'clamp(11px, 3vw, 17px) 8px',
        fontSize: 'clamp(20px, 5.5vw, 23px)', fontWeight: 700,
        color: '#1a1a1a',
      }}>
        {label}
      </div>
    </button>
  )
}

function TakeoutBag() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0 }}>
      <div style={{ display: 'flex', gap: 13, marginBottom: -3, zIndex: 1 }}>
        <div style={{
          width: 9, height: 15,
          border: '2px solid #c8b898', borderRadius: '8px 8px 0 0',
          borderBottom: 'none', background: 'transparent',
        }} />
        <div style={{
          width: 9, height: 15,
          border: '2px solid #c8b898', borderRadius: '8px 8px 0 0',
          borderBottom: 'none', background: 'transparent',
        }} />
      </div>
      <div style={{
        width: 59, height: 67,
        background: '#fff',
        border: '2px solid #ddd',
        borderRadius: '4px 4px 10px 10px',
        boxShadow: '0 3px 10px rgba(0,0,0,0.1)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: 2,
      }}>
        <span style={{
          fontSize: 13, fontWeight: 900,
          color: '#F5B800', lineHeight: 1,
        }}>F</span>
        <span style={{
          fontSize: 6, fontWeight: 800,
          color: '#744032', letterSpacing: 1,
        }}>BURGER</span>
      </div>
    </div>
  )
}
