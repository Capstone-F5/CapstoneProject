import { useState } from 'react'
import useT from '../i18n/useT'

export default function ItemDetailModal({ item, type, onClose, onAdd, setSides = [], setDrinks = [], setSurcharge = 0 }) {
  const t = useT()
  const [qty,       setQty]       = useState(1)
  const [exclusion, setExclusion] = useState(item?.exclusions?.[0] ?? '없음')
  const [side,      setSide]      = useState(setSides[0])
  const [drink,     setDrink]     = useState(setDrinks[0])

  if (!item) return null

  const isSet      = type === 'set'
  const unitPrice  = item.price
    + (isSet ? setSurcharge : 0)
    + (isSet && side && drink ? side.extra + drink.extra : 0)

  const displayImage = isSet ? (item.setImage ?? item.image) : item.image
  const displayName  = isSet ? `${item.name} ${t('set')}` : item.name
  const displayKcal  = isSet && item.kcal ? item.kcal + 350 : item.kcal

  const handleAdd = () => {
    onAdd({
      id: item.id,
      name: item.name,
      image: displayImage,
      type,
      qty,
      unitPrice,
      exclusion,
      side:       isSet ? side?.name  : null,
      sideExtra:  isSet ? side?.extra ?? 0 : 0,
      drink:      isSet ? drink?.name  : null,
      drinkExtra: isSet ? drink?.extra ?? 0 : 0,
    })
  }

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
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: 'clamp(16px, 4vw, 22px) clamp(16px, 5vw, 22px) clamp(20px, 5vw, 28px)',
          position: 'relative',
          boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
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

        {/* ── 상품 정보 카드 ── */}
        <div style={{
          background: '#fff', borderRadius: 16,
          padding: 'clamp(14px, 3.5vw, 18px)',
          marginBottom: 14,
          display: 'flex', gap: 'clamp(12px, 3vw, 16px)', alignItems: 'flex-start',
        }}>
          <img
            src={displayImage}
            alt={displayName}
            style={{
              width: 'clamp(90px, 24vw, 116px)',
              height: 'clamp(90px, 24vw, 116px)',
              borderRadius: 12, objectFit: 'cover', flexShrink: 0,
            }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 'clamp(16px, 4.5vw, 20px)', fontWeight: 900,
              color: '#1a1a1a', marginBottom: 4, wordBreak: 'keep-all',
            }}>
              {displayName}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 'clamp(14px, 4vw, 16px)', fontWeight: 900 }}>
                {unitPrice.toLocaleString()} {t('won')}
              </span>
              {displayKcal && (
                <span style={{ fontSize: 11, color: '#bbb' }}>{displayKcal} kcal</span>
              )}
            </div>
            {item.desc && (
              <div style={{
                fontSize: 'clamp(10px, 2.8vw, 12px)', color: '#999',
                lineHeight: 1.5, wordBreak: 'keep-all',
              }}>
                {item.desc}
              </div>
            )}

            {/* 수량 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 12 }}>
              <CircleBtn label="−" onClick={() => setQty(q => Math.max(1, q - 1))} />
              <span style={{ fontSize: 17, fontWeight: 700 }}>{qty}</span>
              <CircleBtn label="+" onClick={() => setQty(q => q + 1)} />
            </div>
          </div>
        </div>

        {/* ── 제외하기 ── */}
        {item.exclusions && item.exclusions.length > 0 && (
          <OptionSection label={t('exclude')}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {item.exclusions.map(ex => (
                <Chip
                  key={ex} label={ex}
                  active={exclusion === ex}
                  onClick={() => setExclusion(ex)}
                  won={t('won')}
                />
              ))}
            </div>
          </OptionSection>
        )}

        {/* ── 세트 옵션 ── */}
        {isSet && (
          <>
            <OptionSection label={t('sideSection')}>
              <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2 }}>
                {setSides.map(s => (
                  <Chip
                    key={s.name}
                    label={s.name}
                    extra={s.extra}
                    active={side?.name === s.name}
                    onClick={() => setSide(s)}
                    won={t('won')}
                  />
                ))}
              </div>
            </OptionSection>

            <OptionSection label={t('drinkSection')}>
              <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2 }}>
                {setDrinks.map(d => (
                  <Chip
                    key={d.name}
                    label={d.name}
                    extra={d.extra}
                    active={drink?.name === d.name}
                    onClick={() => setDrink(d)}
                    won={t('won')}
                  />
                ))}
              </div>
            </OptionSection>
          </>
        )}

        {/* ── 추가하기 ── */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
          <button onClick={handleAdd} style={{
            background: '#744032', color: '#fff',
            border: 'none', borderRadius: 12,
            padding: 'clamp(13px, 3.5vw, 16px) clamp(28px, 8vw, 40px)',
            fontSize: 'clamp(15px, 4.5vw, 17px)', fontWeight: 900,
            cursor: 'pointer',
            boxShadow: '0 3px 10px rgba(116,64,50,0.3)',
          }}>
            {t('addToCart')}
          </button>
        </div>
      </div>
    </div>
  )
}

function OptionSection({ label, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{
        fontSize: 'clamp(11px, 3vw, 13px)', fontWeight: 700, color: '#666',
        marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{
        background: '#fff', borderRadius: 12,
        padding: 'clamp(10px, 3vw, 14px)',
        boxShadow: '0 1px 5px rgba(0,0,0,0.05)',
      }}>
        {children}
      </div>
    </div>
  )
}

function Chip({ label, extra, active, onClick, won }) {
  const size = 'clamp(64px, 17vw, 80px)'
  return (
    <button
      onClick={onClick}
      style={{
        flexShrink: 0,
        width: size, height: size,
        borderRadius: 10,
        border: active ? '2px solid #744032' : '1.5px solid #e8e8e8',
        background: active ? '#744032' : '#fff',
        color: active ? '#fff' : '#333',
        fontSize: 'clamp(11px, 3vw, 13px)',
        fontWeight: active ? 700 : 400,
        cursor: 'pointer',
        position: 'relative',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        textAlign: 'center',
        wordBreak: 'keep-all', lineHeight: 1.3,
        padding: '4px 6px',
      }}
    >
      <span style={{
        position: 'absolute',
        left: '50%', top: '50%',
        transform: 'translate(-50%, -50%)',
        width: '100%',
        padding: '0 6px',
      }}>{label}</span>
      {extra > 0 && (
        <span style={{
          fontSize: 10,
          color: active ? 'rgba(255,255,255,0.8)' : '#e44',
          position: 'absolute',
          left: '50%', top: '50%',
          transform: 'translate(-50%, 10px)',
        }}>
          +{extra.toLocaleString()}{won}
        </span>
      )}
    </button>
  )
}

function CircleBtn({ label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: 30, height: 30, borderRadius: '50%',
        border: '1.5px solid #ccc', background: '#fff',
        fontSize: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer', padding: 0, lineHeight: 1, color: '#333',
      }}
    >
      {label}
    </button>
  )
}
