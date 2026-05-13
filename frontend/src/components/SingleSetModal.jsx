import { SET_SURCHARGE } from '../data/menuData'

export default function SingleSetModal({ item, onSelect, onClose }) {
  if (!item) return null

  const setPrice = item.price + SET_SURCHARGE
  const setKcal  = item.kcal ? item.kcal + 350 : null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '0 clamp(16px, 5vw, 24px)',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '92%', maxWidth: 680,
          background: '#f5f5f5',
          borderRadius: 20,
          maxHeight: '88vh',
          overflowY: 'auto',
          padding: 'clamp(20px, 5vw, 28px) clamp(16px, 5vw, 24px) clamp(24px, 6vw, 32px)',
          boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
          position: 'relative',
        }}
      >

        {/* 닫기 */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 12, right: 12,
            width: 32, height: 32, borderRadius: '50%',
            background: '#fff', border: '1px solid #eee',
            fontSize: 20, color: '#888', cursor: 'pointer',
            lineHeight: 1, padding: 0,
            boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
          }}
        >×</button>

        {/* Item name + desc */}
        <div style={{
          fontSize: 'clamp(22px, 6.5vw, 28px)', fontWeight: 900,
          color: '#1a1a1a', textAlign: 'center', marginBottom: 6,
        }}>
          {item.name}
        </div>
        {item.desc && (
          <div style={{
            fontSize: 'clamp(12px, 3.2vw, 13px)', color: '#888',
            textAlign: 'center', marginBottom: 'clamp(20px, 5vw, 28px)',
            wordBreak: 'keep-all', lineHeight: 1.5,
          }}>
            {item.desc}
          </div>
        )}

        {/* Two choice cards */}
        <div style={{ display: 'flex', gap: 'clamp(10px, 3vw, 16px)' }}>
          <ChoiceCard
            image={item.image}
            alt={item.name}
            price={item.price}
            kcal={item.kcal}
            label="단품 선택"
            onClick={() => onSelect('single')}
          />
          <ChoiceCard
            image={item.setImage ?? item.image}
            alt={`${item.name} 세트`}
            price={setPrice}
            kcal={setKcal}
            label="세트 선택"
            onClick={() => onSelect('set')}
          />
        </div>
      </div>
    </div>
  )
}

function ChoiceCard({ image, alt, price, kcal, label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1, background: '#fff', border: 'none', borderRadius: 14,
        overflow: 'hidden', cursor: 'pointer',
        boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        display: 'flex', flexDirection: 'column', padding: 0,
      }}
    >
      <img
        src={image}
        alt={alt}
        style={{ width: '100%', aspectRatio: '1', objectFit: 'cover' }}
      />
      <div style={{ padding: '10px 8px 14px', textAlign: 'center' }}>
        <div style={{
          fontSize: 'clamp(13px, 3.8vw, 15px)', fontWeight: 900,
          color: '#1a1a1a', marginBottom: 2,
        }}>
          {price.toLocaleString()} 원
        </div>
        {kcal && (
          <div style={{ fontSize: 11, color: '#bbb', marginBottom: 6 }}>{kcal} kcal</div>
        )}
        <div style={{
          fontSize: 'clamp(12px, 3.5vw, 14px)', fontWeight: 700, color: '#555',
        }}>
          {label}
        </div>
      </div>
    </button>
  )
}
