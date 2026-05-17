import { SET_SURCHARGE } from '../data/menuData'

export default function SingleSetScreen({ item, nav, setSelectedType }) {
  if (!item) return null

  const setPrice = item.price + SET_SURCHARGE
  const setKcal = item.kcal ? item.kcal + 350 : null

  const select = (type) => {
    setSelectedType(type)
    nav('itemDetail')
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#f5f5f5',
      padding: 'clamp(44px, 11vw, 64px) clamp(20px, 6vw, 28px) 40px',
    }}>
      <div style={{
        fontSize: 'clamp(26px, 8vw, 36px)', fontWeight: 900,
        color: '#1a1a1a', textAlign: 'center', marginBottom: 8,
      }}>
        {item.name}
      </div>

      {item.desc && (
        <div style={{
          fontSize: 'clamp(12px, 3.5vw, 14px)', color: '#666',
          textAlign: 'center',
          marginBottom: 'clamp(28px, 8vw, 44px)',
          wordBreak: 'keep-all',
        }}>
          {item.desc}
        </div>
      )}

      <div style={{ display: 'flex', gap: 'clamp(12px, 4vw, 20px)' }}>
        <ChoiceCard
          image={item.image}
          alt={item.name}
          price={item.price}
          kcal={item.kcal}
          label="단품 선택"
          onClick={() => select('single')}
        />
        <ChoiceCard
          image={item.setImage ?? item.image}
          alt={`${item.name} 세트`}
          price={setPrice}
          kcal={setKcal}
          label="세트 선택"
          onClick={() => select('set')}
        />
      </div>
    </div>
  )
}

function ChoiceCard({ image, alt, price, kcal, label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1, background: '#fff', border: 'none', borderRadius: 16,
        overflow: 'hidden', cursor: 'pointer',
        boxShadow: '0 2px 12px rgba(0,0,0,0.09)',
        display: 'flex', flexDirection: 'column', padding: 0,
      }}
    >
      <img
        src={image}
        alt={alt}
        style={{ width: '100%', aspectRatio: '1', objectFit: 'cover' }}
      />
      <div style={{ padding: '12px 8px 18px', textAlign: 'center' }}>
        <div style={{
          fontSize: 'clamp(14px, 4vw, 16px)', fontWeight: 900,
          color: '#1a1a1a', marginBottom: 2,
        }}>
          {price.toLocaleString()} 원
        </div>
        {kcal && (
          <div style={{ fontSize: 11, color: '#aaa', marginBottom: 8 }}>{kcal} kcal</div>
        )}
        <div style={{
          fontSize: 'clamp(13px, 4vw, 15px)', fontWeight: 700,
          color: '#444',
        }}>
          {label}
        </div>
      </div>
    </button>
  )
}
