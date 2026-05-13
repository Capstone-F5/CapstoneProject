import { useState } from 'react'
import Logo from '../components/Logo'

const POINT_KEYS = ['1','2','3','4','5','6','7','8','9','지움','0','010']

// 카드 내부 좌우 패딩 + 리스트 영역 좌우 패딩 = 컬럼 헤더 좌우 패딩
const LIST_PX  = 16   // 리스트 영역 좌우 패딩
const CARD_PX  = 16   // 카드 내부 좌우 패딩
const HDR_PX   = LIST_PX + CARD_PX   // 32px — 헤더와 카드 그리드 x축 정렬

const COL_QTY   = 130   // 수량 컬럼 고정폭 (px)
const COL_PRICE = 140   // 금액 컬럼 고정폭 (px)
const IMG_SIZE  = 90    // 상품 이미지 크기 (px)

export default function CartScreen({ cart, total, updateQty, clearCart, nav }) {
  const [showPointPrompt, setShowPointPrompt] = useState(false)
  const [showPointsPopup, setShowPointsPopup] = useState(false)
  const [pointsInput,     setPointsInput]     = useState('')
  const [pointsError,     setPointsError]     = useState('')

  const handlePayClick = () => {
    if (cart.length === 0) return
    setShowPointPrompt(true)
  }

  const handlePointKey = (key) => {
    if (key === '지움')       setPointsInput(p => p.slice(0, -1))
    else if (key === '010')   setPointsInput('010')
    else if (pointsInput.length < 11) setPointsInput(p => p + key)
    setPointsError('')
  }

  const formatPhone = (v) => {
    const d = v.replace(/\D/g, '').slice(0, 11)
    if (d.length <= 3) return d
    if (d.length <= 7) return `${d.slice(0,3)}-${d.slice(3)}`
    return `${d.slice(0,3)}-${d.slice(3,7)}-${d.slice(7)}`
  }

  const handlePointsConfirm = () => {
    const d = pointsInput.replace(/\D/g, '')
    if (!d.length)    { setPointsError('전화번호를 입력해 주세요'); return }
    if (d.length !== 11) { setPointsError('11자리 번호를 입력해 주세요'); return }
    setShowPointsPopup(false)
    nav('payment')
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      height: '100dvh', height: '100vh',
      overflow: 'hidden',
      background: '#f2f2f2',
    }}>

      {/* ── 헤더 ── */}
      <div style={{
        background: '#744032', padding: '10px 16px',
        display: 'flex', alignItems: 'center', flexShrink: 0,
      }}>
        <button onClick={() => nav('menu')} style={{
          background: 'none', border: 'none',
          color: '#F5B800', fontSize: 30, lineHeight: 1,
          padding: '0 10px 0 0', cursor: 'pointer',
        }}>‹</button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <Logo height={38} />
        </div>
        <div style={{ width: 40 }} />
      </div>

      {/* ── 주문내역 타이틀 ── */}
      <div style={{
        background: '#fff',
        padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid #eee',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 24, fontWeight: 900, color: '#1a1a1a' }}>주문내역</span>
        <button onClick={clearCart} style={{
          border: '1.5px solid #ccc', borderRadius: 8,
          background: '#fff', padding: '10px 20px',
          fontSize: 16, fontWeight: 600, color: '#555',
          cursor: 'pointer',
        }}>전체삭제</button>
      </div>

      {/* ── 컬럼 헤더 ── */}
      <div style={{
        background: '#fff',
        display: 'grid',
        gridTemplateColumns: `${IMG_SIZE}px 1fr ${COL_QTY}px ${COL_PRICE}px`,
        padding: `10px ${HDR_PX}px`,
        columnGap: 12,
        fontSize: 16, fontWeight: 700, color: '#aaa',
        borderBottom: '2px solid #eee',
        flexShrink: 0,
      }}>
        <span style={{ gridColumn: '1 / 3' }}>메뉴</span>
        <span style={{ textAlign: 'center' }}>수량</span>
        <span style={{ textAlign: 'right', paddingRight: 26 }}>금액</span>
      </div>

      {/* ── 아이템 목록 ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: `14px ${LIST_PX}px` }}>
        {cart.length === 0 ? (
          <div style={{
            textAlign: 'center', color: '#bbb',
            padding: '100px 0', fontSize: 20,
          }}>
            장바구니가 비어있습니다
          </div>
        ) : (
          cart.map(item => (
            <CartItem key={item.cartId} item={item} onUpdateQty={updateQty} />
          ))
        )}
      </div>

      {/* ── 하단: 합계 + 버튼 ── */}
      <div style={{
        background: '#fff',
        borderTop: '2px solid #ddd',
        padding: '16px 20px',
        flexShrink: 0,
      }}>
        {/* 총 결제금액 */}
        <div style={{
          display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline',
          gap: 14, marginBottom: 16,
        }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#555' }}>총 결제금액</span>
          <span style={{ fontSize: 34, fontWeight: 900, color: '#1a1a1a' }}>
            {total.toLocaleString()} 원
          </span>
        </div>

        {/* 버튼 행 */}
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            onClick={() => setShowPointsPopup(true)}
            style={{
              flex: 1, padding: '22px 0',
              border: 'none', borderRadius: 12,
              background: '#d0d0d0', color: '#444',
              fontSize: 22, fontWeight: 700, cursor: 'pointer',
            }}
          >포인트</button>
          <button
            onClick={handlePayClick}
            disabled={cart.length === 0}
            style={{
              flex: 2, padding: '22px 0',
              border: 'none', borderRadius: 12,
              background: cart.length > 0 ? '#F5B800' : '#ccc',
              color: '#1a1a1a',
              fontSize: 22, fontWeight: 900,
              cursor: cart.length > 0 ? 'pointer' : 'default',
            }}
          >결제하기</button>
        </div>
      </div>

      {/* ── 포인트 적립 확인 팝업 ── */}
      {showPointPrompt && (
        <ModalBase onClose={() => setShowPointPrompt(false)}>
          <p style={{ fontSize: 22, fontWeight: 900, textAlign: 'center', marginBottom: 20 }}>
            포인트를 적립하시겠습니까?
          </p>
          <div style={{ display: 'flex', gap: 12 }}>
            <ModalBtn label="아니오" color="#d4d4d4" textColor="#555"
              onClick={() => { setShowPointPrompt(false); nav('payment') }} />
            <ModalBtn label="예" color="#F5B800" textColor="#1a1a1a"
              onClick={() => { setShowPointPrompt(false); setShowPointsPopup(true) }} />
          </div>
        </ModalBase>
      )}

      {/* ── 전화번호 입력 팝업 ── */}
      {showPointsPopup && (
        <ModalBase onClose={() => setShowPointsPopup(false)}>
          <p style={{ fontSize: 22, fontWeight: 900, textAlign: 'center', marginBottom: 4 }}>
            휴대폰 번호를 입력해 주세요
          </p>
          <p style={{ fontSize: 15, color: '#666', textAlign: 'center', marginBottom: 14 }}>
            적립할 번호를 입력해 주세요
          </p>
          <div style={{
            width: '100%', border: '2px solid #e44', borderRadius: 10,
            padding: '14px', fontSize: 22, fontWeight: 700,
            minHeight: 58, marginBottom: 6,
            textAlign: 'center', letterSpacing: 2, color: '#1a1a1a',
          }}>
            {formatPhone(pointsInput) || ' '}
          </div>
          {pointsError && (
            <p style={{ fontSize: 13, color: '#e44', textAlign: 'center', marginBottom: 8 }}>
              {pointsError}
            </p>
          )}
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
            gap: 10, marginBottom: 16,
          }}>
            {POINT_KEYS.map(k => (
              <button key={k} onClick={() => handlePointKey(k)} style={{
                padding: '16px 0', background: '#9e9e9e', color: '#fff',
                border: 'none', borderRadius: 8,
                fontSize: 20, fontWeight: 700, cursor: 'pointer',
              }}>{k}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <ModalBtn label="취소" color="#d4d4d4" textColor="#555"
              onClick={() => setShowPointsPopup(false)} />
            <ModalBtn label="확인" color="#F5B800" textColor="#1a1a1a"
              onClick={handlePointsConfirm} />
          </div>
        </ModalBase>
      )}
    </div>
  )
}

/* ────────────────────────────────────────────
   CartItem
   Row 1: 이미지(col1) | 수량+/-(col2) | 금액✕(col3)
   Row 2: 상품명(col1, 이미지 중앙) | 옵션박스(col2+3)
──────────────────────────────────────────── */
function CartItem({ item, onUpdateQty }) {
  const hasOptions = (item.exclusion && item.exclusion !== '없음') || item.side || item.drink

  return (
    <div style={{
      background: '#fff',
      borderRadius: 14,
      marginBottom: 12,
      padding: `14px ${CARD_PX}px`,
      boxShadow: '0 1px 6px rgba(0,0,0,0.07)',
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: `${IMG_SIZE}px 1fr ${COL_QTY}px ${COL_PRICE}px`,
        columnGap: 12,
        rowGap: 10,
      }}>

        {/* ── Row 1+2, Col 1: 이미지 + 상품명 (전체 높이 중앙) ── */}
        <div style={{
          gridColumn: 1, gridRow: '1 / 3',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 6,
        }}>
          {item.image
            ? <img src={item.image} alt={item.name} style={{
                width: IMG_SIZE, height: IMG_SIZE,
                borderRadius: 10, objectFit: 'cover', display: 'block',
              }} />
            : <span style={{ fontSize: 44 }}>🍔</span>
          }
          <span style={{ fontSize: 14, fontWeight: 700, color: '#333', wordBreak: 'keep-all', textAlign: 'center', width: IMG_SIZE }}>
            {item.name}{item.type === 'set' ? ' 세트' : ''}
          </span>
        </div>

        {/* ── Col 3: 수량 ── */}
        <div style={{
          gridColumn: 3, gridRow: hasOptions ? 1 : '1 / 3',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          alignSelf: 'center',
        }}>
          <QtyBtn label="−" onClick={() => onUpdateQty(item.cartId, item.qty - 1)} />
          <span style={{ fontSize: 20, fontWeight: 700, minWidth: 22, textAlign: 'center' }}>
            {item.qty}
          </span>
          <QtyBtn label="+" onClick={() => onUpdateQty(item.cartId, item.qty + 1)} />
        </div>

        {/* ── Col 4: 금액 + ✕ ── */}
        <div style={{
          gridColumn: 4, gridRow: hasOptions ? 1 : '1 / 3',
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8,
          alignSelf: 'center',
        }}>
          <span style={{ fontSize: 18, fontWeight: 800 }}>
            {(item.unitPrice * item.qty).toLocaleString()}원
          </span>
          <button
            onClick={() => onUpdateQty(item.cartId, 0)}
            style={{
              background: 'none', border: 'none',
              color: '#bbb', fontSize: 20, lineHeight: 1,
              cursor: 'pointer', padding: 0, flexShrink: 0,
            }}
          >✕</button>
        </div>

        {/* ── Row 2, Col 2~4: 옵션 박스 (이미지 제외 전체 폭) ── */}
        {hasOptions && (
          <div style={{
            gridColumn: '2 / -1', gridRow: 2,
            background: '#ededed',
            borderRadius: 10,
            overflow: 'hidden',
            alignSelf: 'center',
            marginTop: 4,
          }}>
            {item.exclusion && item.exclusion !== '없음' && (
              <SubRow label={item.exclusion} extra={0} />
            )}
            {item.side  && <SubRow label={item.side}  extra={item.sideExtra}  />}
            {item.drink && <SubRow label={item.drink} extra={item.drinkExtra} />}
          </div>
        )}

      </div>
    </div>
  )
}

/* ────────────────────────────────────────────
   SubRow — 세부 옵션 행
   colums: 세부상품명(1fr) | 수량(fixed) | 금액(fixed)
──────────────────────────────────────────── */
function SubRow({ label, extra }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `1fr ${COL_QTY}px ${COL_PRICE}px`,
      columnGap: 12,
      alignItems: 'center',
      padding: '11px 0 11px 14px',
      fontSize: 15, color: '#555',
      borderBottom: '1px solid rgba(0,0,0,0.06)',
    }}>
      <span style={{ fontWeight: 500 }}>- {label}</span>
      <span style={{ textAlign: 'center', fontWeight: 600 }}>1</span>
      <span style={{
        textAlign: 'right', fontWeight: 600, paddingRight: 26,
        color: extra > 0 ? '#cc3333' : '#999',
      }}>
        {extra > 0 ? `+${extra.toLocaleString()}원` : '0'}
      </span>
    </div>
  )
}

/* ── 수량 버튼 ── */
function QtyBtn({ label, onClick }) {
  return (
    <button onClick={onClick} style={{
      width: 32, height: 32, borderRadius: 6,
      border: '1.5px solid #ccc', background: '#fff',
      fontSize: 20, display: 'flex', alignItems: 'center', justifyContent: 'center',
      cursor: 'pointer', padding: 0, lineHeight: 1, flexShrink: 0,
    }}>{label}</button>
  )
}

/* ── 팝업 버튼 ── */
function ModalBtn({ label, color, textColor, onClick }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: '14px 0',
      border: 'none', borderRadius: 10,
      background: color, color: textColor,
      fontSize: 18, fontWeight: 700, cursor: 'pointer',
    }}>{label}</button>
  )
}

/* ── 팝업 기본 레이아웃 ── */
function ModalBase({ onClose, children }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 120,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '0 clamp(16px,5vw,24px)',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '94%', maxWidth: 640,
          background: '#fff', borderRadius: 18,
          padding: 'clamp(22px,5vw,28px)',
          boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
        }}
      >
        {children}
      </div>
    </div>
  )
}
