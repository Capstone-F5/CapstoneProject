import { useState, useEffect } from 'react'
import Logo from '../components/Logo'
import ReturnToStartDialog from '../components/ReturnToStartDialog'
import SingleSetModal from '../components/SingleSetModal'
import ItemDetailModal from '../components/ItemDetailModal'
import IdleOverlay from '../components/IdleOverlay'
import { useMenuData } from '../hooks/useMenuData'
import useT from '../i18n/useT'

const COLS = 3
const GRID_GAP = 9

const CAT_IMAGE = {
  recommended: '/images/sets/F버거 세트.png',
  burger:      '/images/burgers/불고기버거.png',
  side:        '/images/sides/감튀.png',
  drink:       '/images/drinks/콜라.png',
}

export default function MenuScreen({ cart, total, addToCart, updateQty, clearCart, nav }) {
  const t = useT()
  const { menuData, isLoading, error, retry } = useMenuData()

  const [catId,     setCatId]     = useState('recommended')
  const [page,      setPage]      = useState(0)
  const [showHome,  setShowHome]  = useState(false)
  const [modalItem, setModalItem] = useState(null)
  const [modalStep, setModalStep] = useState(null)   // 'singleSet' | 'detail'
  const [modalType, setModalType] = useState('single')

  const handleItemTap = (item) => {
    setModalItem(item)
    if (item.hasSet) {
      setModalStep('singleSet')
    } else {
      setModalType('single')
      setModalStep('detail')
    }
  }

  const handleTypeSelect = (type) => {
    setModalType(type)
    setModalStep('detail')
  }

  const handleAdd = (cartItem) => {
    addToCart(cartItem)
    setModalItem(null)
    setModalStep(null)
  }

  const closeModal = () => { setModalItem(null); setModalStep(null) }

  const itemsPerPage = 3 * COLS
  const items        = menuData ? (menuData.menuItems?.[catId] ?? []) : []
  const totalPages   = Math.max(1, Math.ceil(items.length / itemsPerPage))

  useEffect(() => {
    setPage(p => Math.min(p, Math.max(0, totalPages - 1)))
  }, [totalPages])

  if (isLoading) {
    return (
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        minHeight: '100dvh', background: '#f2f2f2',
        alignItems: 'center', justifyContent: 'center', gap: 16,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: '50%',
          border: '4px solid #e0e0e0',
          borderTopColor: '#744032',
          animation: 'spin 0.8s linear infinite',
        }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        <span style={{ fontSize: 14, color: '#999' }}>{t('loading')}</span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        minHeight: '100dvh', background: '#f2f2f2',
        alignItems: 'center', justifyContent: 'center', gap: 16, padding: 32,
      }}>
        <div style={{ fontSize: 14, color: '#888', textAlign: 'center' }}>
          {t('loadError')}<br />{error.message}
        </div>
        <button onClick={retry} style={{
          padding: '12px 28px', borderRadius: 10,
          border: 'none', background: '#744032', color: '#fff',
          fontSize: 14, fontWeight: 700, cursor: 'pointer',
        }}>{t('retry')}</button>
      </div>
    )
  }

  const { categories, menuItems, setSides, setDrinks, setSurcharge } = menuData
  const pageItems  = items.slice(page * itemsPerPage, (page + 1) * itemsPerPage)

  const handleCat = (id) => { setCatId(id); setPage(0) }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100dvh', height: '100vh',
      overflow: 'hidden',
      background: '#f2f2f2',
    }}>

      {/* ── Header ── */}
      <div style={{
        background: '#744032',
        padding: '20px 32px',
        display: 'flex', alignItems: 'center',
        flexShrink: 0,
      }}>
        <button onClick={() => setShowHome(true)} style={{
          background: 'none', border: 'none',
          color: '#F5B800', fontSize: 60, lineHeight: 1,
          padding: '0 16px 0 0', cursor: 'pointer',
        }}>‹</button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <Logo height={76} />
        </div>
        <div style={{ width: 80 }} />
      </div>

      {/* ── Category Tabs ── */}
      <div style={{
        background: '#fff',
        display: 'flex',
        padding: '12px 8px 10px',
        borderBottom: '1px solid #ebebeb',
        flexShrink: 0,
      }}>
        {categories.map(cat => {
          const active = cat.id === catId
          return (
            <button
              key={cat.id}
              onClick={() => handleCat(cat.id)}
              style={{
                flex: 1, display: 'flex', flexDirection: 'column',
                alignItems: 'center', gap: 6,
                padding: '4px 4px', border: 'none', background: 'none',
                cursor: 'pointer',
              }}
            >
              <img
                src={CAT_IMAGE[cat.id]}
                alt={cat.name}
                style={{
                  width: 'clamp(72px, 20vw, 92px)',
                  height: 'clamp(72px, 20vw, 92px)',
                  objectFit: 'cover',
                  filter: active ? 'none' : 'grayscale(1) opacity(0.4)',
                  transform: active ? 'scale(1.1)' : 'scale(1)',
                  transition: 'all 0.18s',
                }}
              />
              <span style={{
                fontSize: 'clamp(18px, 4.8vw, 22px)',
                fontWeight: active ? 700 : 400,
                color: active ? '#1a1a1a' : '#aaa',
              }}>{cat.name}</span>
            </button>
          )
        })}
      </div>

      {/* ── Menu Grid ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 12px 8px' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: 'clamp(10px, 2.6vw, 14px)',
          alignItems: 'stretch',
        }}>
          {pageItems.map(item => (
            <div key={item.id + '-' + catId} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FoodCard item={item} onClick={() => handleItemTap(item)} />
            </div>
          ))}
        </div>
      </div>

      {/* ── Pagination + Cart (bottom section) ── */}
      <div style={{ flexShrink: 0 }}>

        {/* Pagination — cart 바로 위 */}
        {totalPages > 1 && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 10, padding: '6px 0',
            background: '#f2f2f2',
          }}>
            <button onClick={() => setPage(p => Math.max(0, p - 1))} style={{
              background: 'none', border: 'none',
              color: '#F5B800', fontSize: 16, cursor: 'pointer', padding: '0 4px',
            }}>◄</button>
            {Array.from({ length: totalPages }).map((_, i) => (
              <div key={i} style={{
                width: i === page ? 18 : 8, height: 8, borderRadius: 4,
                background: i === page ? '#744032' : '#ccc',
                transition: 'all 0.2s',
              }} />
            ))}
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} style={{
              background: 'none', border: 'none',
              color: '#F5B800', fontSize: 16, cursor: 'pointer', padding: '0 4px',
            }}>►</button>
          </div>
        )}

        {/* Cart Section */}
        {cart.length > 0 && (
          <div style={{
            background: '#fff',
            borderTop: '1px solid #e8e8e8',
            boxShadow: '0 -2px 8px rgba(0,0,0,0.06)',
          }}>
            {/* 항목 목록 — 고정 높이 (3개 기준), 초과 시 스크롤 */}
            <div>
              {cart.map(item => (
                <MiniCartItem key={item.cartId} item={item} updateQty={updateQty} />
              ))}
            </div>

            {/* 합계 + 결제하기 */}
            <div style={{
              padding: '17px 24px 20px',
              borderTop: '1px solid #f0f0f0',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ fontSize: 24, color: '#888' }}>
                {t('cartSummary', cart.reduce((s, c) => s + c.qty, 0), cart.reduce((s, c) => s + c.unitPrice * c.qty, 0))}
              </span>
              <button onClick={() => nav('cart')} style={{
                background: '#F5B800', color: '#1a1a1a',
                border: 'none', borderRadius: 15,
                padding: '21px 39px',
                fontSize: 27, fontWeight: 900,
                cursor: 'pointer',
              }}>
                {t('checkout')}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Dialogs / Modals ── */}
      {showHome && (
        <ReturnToStartDialog
          onConfirm={() => { clearCart(); nav('start') }}
          onCancel={() => setShowHome(false)}
        />
      )}

      {modalItem && modalStep === 'singleSet' && (
        <SingleSetModal
          item={modalItem}
          onSelect={handleTypeSelect}
          onClose={closeModal}
          setSurcharge={setSurcharge}
        />
      )}

      {modalItem && modalStep === 'detail' && (
        <ItemDetailModal
          item={modalItem}
          type={modalType}
          onAdd={handleAdd}
          onClose={closeModal}
          setSides={setSides}
          setDrinks={setDrinks}
          setSurcharge={setSurcharge}
        />
      )}

      <IdleOverlay onExpire={() => { clearCart(); nav('start') }} />
    </div>
  )
}

function MiniCartItem({ item, updateQty }) {
  const t = useT()
  const options = [
    item.exclusion && item.exclusion !== '없음' ? item.exclusion : null,
    item.side  ?? null,
    item.drink ?? null,
  ].filter(Boolean)

  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      padding: '15px 24px', gap: 17,
      borderBottom: '1px solid #f5f5f5',
      minHeight: 108,
    }}>
      {item.image ? (
        <img src={item.image} alt={item.name} style={{
          width: 66, height: 66, borderRadius: 9, objectFit: 'cover', flexShrink: 0,
        }} />
      ) : (
        <span style={{ fontSize: 39, flexShrink: 0 }}>🍔</span>
      )}

      {/* 이름 + 옵션 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 24, fontWeight: 700, color: '#1a1a1a',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {item.name}{item.type === 'set' ? ` ${t('set')}` : ''}
        </div>
        {options.length > 0 && (
          <div style={{
            fontSize: 20, color: '#aaa', marginTop: 3,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {options.join(' · ')}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexShrink: 0 }}>
        <QtyBtn label="−" onClick={() => updateQty(item.cartId, item.qty - 1)} />
        <span style={{ fontSize: 26, fontWeight: 700, minWidth: 33, textAlign: 'center' }}>{item.qty}</span>
        <QtyBtn label="+" onClick={() => updateQty(item.cartId, item.qty + 1)} />
      </div>
      <span style={{ fontSize: 24, fontWeight: 700, color: '#222', flexShrink: 0, minWidth: 102, textAlign: 'right' }}>
        {(item.unitPrice * item.qty).toLocaleString()}{t('won')}
      </span>
      <button onClick={() => updateQty(item.cartId, 0)} style={{
        background: 'none', border: 'none',
        color: '#ccc', fontSize: 27, lineHeight: 1,
        padding: 2, flexShrink: 0, cursor: 'pointer',
      }}>✕</button>
    </div>
  )
}

function FoodCard({ item, onClick }) {
  return (
    <button onClick={onClick} style={{
      background: '#ffffff',
      border: '1px solid #f1f1f1', borderRadius: 16,
      padding: 0, overflow: 'hidden', cursor: 'pointer',
      boxShadow: '0 6px 16px rgba(0,0,0,0.08)',
      display: 'flex', flexDirection: 'column',
      textAlign: 'center',
      width: '91%',
    }}>
      <div style={{
        width: '100%', aspectRatio: '1 / 0.46',
        background: '#ffffff',
        padding: 8,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        borderBottom: '1px solid #f2f2f2',
      }}>
        {item.image ? (
          <img
            src={item.image}
            alt={item.name}
            style={{
              width: '100%', height: '100%',
              objectFit: 'contain',
              borderRadius: 10,
            }}
          />
        ) : (
          <span style={{ fontSize: 'clamp(21px, 5.6vw, 31px)' }}>
            {item.emoji ?? '🍔'}
          </span>
        )}
      </div>
      <div style={{ padding: '10px 8px 12px', flexShrink: 0 }}>
        <div style={{
          fontSize: 'clamp(17px, 4.7vw, 21px)',
          fontWeight: 800, color: '#1a1a1a',
          lineHeight: 1.25, marginBottom: 5,
          wordBreak: 'keep-all', textAlign: 'center',
        }}>
          {item.name}
        </div>
        <div style={{
          fontSize: 'clamp(16px, 4.2vw, 18px)',
          color: '#744032', textAlign: 'center', fontWeight: 700,
        }}>{item.price.toLocaleString()}~</div>
      </div>
    </button>
  )
}

function QtyBtn({ label, onClick }) {
  return (
    <button onClick={(e) => { e.stopPropagation(); onClick() }} style={{
      width: 44, height: 44,
      border: '1px solid #ccc', borderRadius: 6,
      background: '#fff', fontSize: 27,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      cursor: 'pointer', padding: 0, lineHeight: 1,
    }}>
      {label}
    </button>
  )
}
