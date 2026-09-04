import Logo from '../components/Logo'
import useT from '../i18n/useT'

// ★ 1. 상단에 손 이미지 파일들을 직접 import 합니다.
import hand1 from '../../public/images/hand/hand1.webp'
import hand2 from '../../public/images/hand/hand2.webp'

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
      height: '100%',
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
          {/* ★ 2. 경로 문자열 대신 import한 변수(hand1, hand2)를 넘겨줍니다. */}
          <TypeCard
            label={t('dineIn')}
            onClick={() => select('dine-in')}
            handImage={hand1}
          >
            <img
              src="/images/sets/F버거 세트.webp"
              alt="dine-in"
              style={{ width: '70%', aspectRatio: '1 / 1', objectFit: 'scale-down' }}
            />
          </TypeCard>

          <TypeCard
            label={t('takeout')}
            onClick={() => select('takeout')}
            handImage={hand2}
          >
            <img
              src="/images/etc/Takeout.webp"
              alt="포장"
              style={{ width: '70%', aspectRatio: '1 / 1', objectFit: 'scale-down' }}
            />
          </TypeCard>
        </div>
      </div>
    </div>
  )
}

function TypeCard({ label, onClick, handImage, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1, background: '#fff', border: 'none',
        borderRadius: 16, cursor: 'pointer',
        boxShadow: '0 2px 14px rgba(0,0,0,0.1)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', padding: 0,
        aspectRatio: ORDER_TYPE_CARD_RATIO,
        position: 'relative',
      }}
    >
      {handImage && (
        <img
          src={handImage}
          alt="손 표시"
          style={{
            position: 'absolute',
            top: '12px',
            left: '12px',
            width: '45px',
            height: 'auto',
            zIndex: 10,
          }}
        />
      )}

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
