import { useState, useEffect } from 'react'
import { SET_SIDES, SET_DRINKS, SET_SURCHARGE } from '../data/menuData'

// App.jsx에서 손가락 개수 데이터를 꽂아줄 fingerCountRef props 추가
export default function ItemDetailScreen({ item, type, addToCart, nav, fingerCountRef }) {
  const [qty, setQty]           = useState(1)
  const [exclusion, setExclusion] = useState(item?.exclusions?.[0] ?? '없음')
  const [side, setSide]         = useState(SET_SIDES[0])
  const [drink, setDrink]       = useState(SET_DRINKS[0])

  // 🔥🔥🔥 제스처 인식 피드백용 팝업(토스트) 상태 추가
  const [toastMsg, setToastMsg] = useState(null)

  useEffect(() => {
    if (!fingerCountRef) return
    // App.jsx에서 hand.stable_fingers 값이 들어올 때마다 이 함수가 실행됩니다.
    fingerCountRef.current = (count) => {
      // 1~5개의 확정된 손가락 개수가 들어오면 수량을 즉시 변경!
      if (count >= 1 && count <= 5) {
        setQty(count)
        setToastMsg(`손가락 제스처: 수량이 ${count}개로 변경되었습니다 🖐️`)
        
        // 2초 뒤에 팝업 자동 숨김
        setTimeout(() => setToastMsg(null), 2000)
      }
    }
    return () => { fingerCountRef.current = null }
  }, [fingerCountRef])
  // 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥

  if (!item) return null

  const isSet = type === 'set'
  const basePrice = item.price + (isSet ? SET_SURCHARGE : 0)
  const extraPrice = isSet ? (side.extra + drink.extra) : 0
  const unitPrice = basePrice + extraPrice

  const handleAdd = () => {
    addToCart({
      id: item.id,
      name: item.name,
      type,
      exclusion,
      side: isSet ? side.name : null,
      sideExtra: isSet ? side.extra : 0,
      drink: isSet ? drink.name : null,
      drinkExtra: isSet ? drink.extra : 0,
      unitPrice,
      qty,
      image: isSet ? (item.setImage ?? item.image) : item.image,
    })
    nav('menu')
  }

  const displayImage = isSet ? (item.setImage ?? item.image) : item.image
  const displayName  = isSet ? `${item.name} 세트` : item.name
  const displayKcal  = isSet && item.kcal ? item.kcal + 350 : item.kcal

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#f5f5f5',
      position: 'relative',
    }}>
      {/* 🔥🔥🔥 손가락 인식 시 나타나는 시각적 팝업(Toast) UI */}
      {toastMsg && (
        <div style={{
          position: 'absolute', top: 80, left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(116, 64, 50, 0.95)', color: '#fff',
          padding: '12px 24px', borderRadius: 30, zIndex: 999,
          fontSize: 'clamp(14px, 4vw, 16px)', fontWeight: 700,
          boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
          animation: 'fadeInDown 0.3s ease-out',
          pointerEvents: 'none',
          whiteSpace: 'nowrap'
        }}>
          {toastMsg}
          <style>{`
            @keyframes fadeInDown {
              from { opacity: 0; transform: translate(-50%, -20px); }
              to { opacity: 1; transform: translate(-50%, 0); }
            }
          `}</style>
        </div>
      )}
      {/* 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥 */}

      {/* Back button */}
      <button
        onClick={() => item.hasSet ? nav('singleSet') : nav('menu')}
        style={{
          position: 'absolute', top: 16, left: 16, zIndex: 10,
          background: 'none', border: 'none',
          color: '#744032', fontSize: 28, lineHeight: 1,
          cursor: 'pointer', padding: '4px 8px',
        }}
      >
        ‹
      </button>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 'clamp(20px, 5vw, 28px)' }}>

        {/* Top info card */}
        <div style={{
          background: '#fff', borderRadius: 16,
          padding: 'clamp(14px, 4vw, 20px)',
          marginBottom: 20,
          marginTop: 16,
        }}>
          <div style={{ display: 'flex', gap: 'clamp(12px, 3vw, 16px)', alignItems: 'flex-start' }}>
            <img
              src={displayImage}
              alt={displayName}
              style={{
                width: 'clamp(110px, 28vw, 140px)',
                height: 'clamp(110px, 28vw, 140px)',
                borderRadius: 12, objectFit: 'cover', flexShrink: 0,
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 'clamp(18px, 5vw, 22px)', fontWeight: 900,
                color: '#1a1a1a', marginBottom: 4, wordBreak: 'keep-all',
              }}>
                {displayName}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
                <span style={{
                  fontSize: 'clamp(15px, 4.5vw, 18px)', fontWeight: 900, color: '#1a1a1a',
                }}>
                  {unitPrice.toLocaleString()} 원
                </span>
                {displayKcal && (
                  <span style={{ fontSize: 12, color: '#999' }}>{displayKcal} kcal</span>
                )}
              </div>
              {item.desc && (
                <div style={{
                  fontSize: 'clamp(11px, 3vw, 13px)', color: '#777',
                  lineHeight: 1.4, wordBreak: 'keep-all',
                }}>
                  {item.desc}
                </div>
              )}
            </div>
          </div>

          {/* Quantity */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 20, marginTop: 16,
          }}>
            <button
              onClick={() => setQty(q => Math.max(1, q - 1))}
              style={{
                width: 36, height: 36, borderRadius: '50%',
                border: '1.5px solid #bbb', background: '#fff',
                fontSize: 20, lineHeight: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
              }}
            >−</button>
            <span style={{ fontSize: 20, fontWeight: 700, minWidth: 24, textAlign: 'center' }}>{qty}</span>
            <button
              onClick={() => setQty(q => q + 1)}
              style={{
                width: 36, height: 36, borderRadius: '50%',
                border: '1.5px solid #bbb', background: '#fff',
                fontSize: 20, lineHeight: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
              }}
            >+</button>
          </div>
        </div>

        {/* 제외하기 */}
        {item.exclusions && item.exclusions.length > 0 && (
          <OptionSection label="제외하기">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {item.exclusions.map(ex => (
                <Chip
                  key={ex}
                  label={ex}
                  selected={exclusion === ex}
                  onClick={() => setExclusion(ex)}
                />
              ))}
            </div>
          </OptionSection>
        )}

        {/* 사이드 (set only) */}
        {isSet && (
          <OptionSection label="사이드">
            <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 4 }}>
              {SET_SIDES.map(s => (
                <Chip
                  key={s.name}
                  label={s.name}
                  extra={s.extra}
                  selected={side.name === s.name}
                  onClick={() => setSide(s)}
                />
              ))}
            </div>
          </OptionSection>
        )}

        {/* 음료 (set only) */}
        {isSet && (
          <OptionSection label="음료">
            <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 4 }}>
              {SET_DRINKS.map(d => (
                <Chip
                  key={d.name}
                  label={d.name}
                  extra={d.extra}
                  selected={drink.name === d.name}
                  onClick={() => setDrink(d)}
                />
              ))}
            </div>
          </OptionSection>
        )}

        <div style={{ height: 80 }} />
      </div>

      {/* Bottom bar */}
      <div style={{
        background: '#f5f5f5',
        padding: '12px clamp(16px, 5vw, 24px) clamp(20px, 5vw, 28px)',
        display: 'flex', justifyContent: 'flex-end',
        flexShrink: 0,
      }}>
        <button
          onClick={handleAdd}
          style={{
            padding: 'clamp(14px, 4vw, 18px) clamp(28px, 8vw, 44px)',
            background: '#744032', color: '#fff',
            border: 'none', borderRadius: 14,
            fontSize: 'clamp(16px, 5vw, 19px)', fontWeight: 900,
            cursor: 'pointer',
            boxShadow: '0 3px 12px rgba(116,64,50,0.3)',
          }}
        >
          추가하기
        </button>
      </div>
    </div>
  )
}

function OptionSection({ label, children }) {
  return (
    <div style={{ marginBottom: 16, position: 'relative' }}>
      <span style={{
        display: 'inline-block',
        fontSize: 'clamp(12px, 3.5vw, 14px)', fontWeight: 700,
        color: '#555',
        background: '#f5f5f5',
        padding: '0 8px 0 0',
        marginBottom: 6,
        position: 'relative', zIndex: 1,
      }}>
        {label}
      </span>
      <div style={{
        background: '#fff', borderRadius: 14,
        padding: 'clamp(12px, 3.5vw, 16px)',
        boxShadow: '0 1px 6px rgba(0,0,0,0.06)',
      }}>
        {children}
      </div>
    </div>
  )
}

function Chip({ label, extra, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        flexShrink: 0,
        padding: 'clamp(10px, 3vw, 14px) clamp(10px, 3vw, 14px)',
        background: selected ? '#744032' : '#fff',
        color: selected ? '#fff' : '#333',
        border: selected ? '2px solid #744032' : '1.5px solid #e0e0e0',
        borderRadius: 10,
        fontSize: 'clamp(12px, 3.5vw, 14px)', fontWeight: selected ? 700 : 400,
        cursor: 'pointer',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 2,
        minWidth: 'clamp(60px, 16vw, 76px)',
        textAlign: 'center',
      }}
    >
      <span>{label}</span>
      {extra > 0 && (
        <span style={{
          fontSize: 10,
          color: selected ? 'rgba(255,255,255,0.8)' : '#e44',
        }}>
          +{extra.toLocaleString()}원
        </span>
      )}
    </button>
  )
}