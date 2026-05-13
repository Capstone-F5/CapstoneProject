import Logo from '../components/Logo'

export default function CartScreen({ cart, total, updateQty, clearCart, nav }) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      minHeight: '100dvh', minHeight: '100vh',
      background: '#f5f5f5',
    }}>
      <Header onBack={() => nav('menu')} />

      {/* Title Row */}
      <div style={{
        background: '#fff', padding: '13px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid #eee', flexShrink: 0,
      }}>
        <span style={{ fontSize: 17, fontWeight: 900 }}>주문내역</span>
        <button onClick={clearCart} style={{
          border: '1px solid #ccc', borderRadius: 6,
          background: '#fff', padding: '6px 14px',
          fontSize: 12, color: '#555', cursor: 'pointer',
        }}>전체삭제</button>
      </div>

      {/* Column Header */}
      <div style={{
        background: '#fff',
        display: 'grid', gridTemplateColumns: '1fr 90px 90px',
        padding: '7px 16px',
        fontSize: 12, fontWeight: 700, color: '#999',
        borderBottom: '1px solid #eee', flexShrink: 0,
      }}>
        <span>메뉴</span>
        <span style={{ textAlign: 'center' }}>수량</span>
        <span style={{ textAlign: 'right', paddingRight: 24 }}>금액</span>
      </div>

      {/* Items */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>
        {cart.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#bbb', padding: '80px 0', fontSize: 14 }}>
            장바구니가 비어있습니다
          </div>
        ) : (
          cart.map(item => <CartItem key={item.cartId} item={item} onUpdateQty={updateQty} />)
        )}
      </div>

      {/* Total + Buttons */}
      <div style={{
        background: '#fff', borderTop: '2px solid #eee',
        padding: '14px 16px', flexShrink: 0,
      }}>
        <div style={{
          display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
          gap: 10, marginBottom: 14,
        }}>
          <span style={{ fontSize: 14, color: '#888' }}>총 결제금액</span>
          <span style={{ fontSize: 22, fontWeight: 900 }}>{total.toLocaleString()} 원</span>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={() => nav('points')} style={{
            flex: 1, padding: '15px 0',
            border: 'none', borderRadius: 12,
            background: '#d8d8d8', color: '#555',
            fontSize: 16, fontWeight: 700, cursor: 'pointer',
          }}>포인트</button>
          <button onClick={() => nav('payment')} disabled={cart.length === 0} style={{
            flex: 2, padding: '15px 0',
            border: 'none', borderRadius: 12,
            background: cart.length > 0 ? '#F5B800' : '#ccc',
            color: '#1a1a1a', fontSize: 16, fontWeight: 900,
            cursor: cart.length > 0 ? 'pointer' : 'default',
          }}>결제하기</button>
        </div>
      </div>

    </div>
  )
}

function CartItem({ item, onUpdateQty }) {
  const hasOptions = (item.exclusion && item.exclusion !== '없음') || item.side || item.drink
  return (
    <div style={{
      background: '#fff', borderRadius: 12,
      marginBottom: 10, padding: '12px 14px',
      boxShadow: '0 1px 5px rgba(0,0,0,0.06)',
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 90px 90px', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {item.image ? (
            <img src={item.image} alt={item.name} style={{
              width: 32, height: 32, borderRadius: 6, objectFit: 'cover', flexShrink: 0,
            }} />
          ) : (
            <span style={{ fontSize: 26 }}>🍔</span>
          )}
          <span style={{ fontSize: 13, fontWeight: 700, wordBreak: 'keep-all' }}>
            {item.name}{item.type === 'set' ? ' 세트' : ''}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
          <SmallBtn label="−" onClick={() => onUpdateQty(item.cartId, item.qty - 1)} />
          <span style={{ fontSize: 13, fontWeight: 700, minWidth: 14, textAlign: 'center' }}>{item.qty}</span>
          <SmallBtn label="+" onClick={() => onUpdateQty(item.cartId, item.qty + 1)} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>
            {(item.unitPrice * item.qty).toLocaleString()}원
          </span>
          <button onClick={() => onUpdateQty(item.cartId, 0)} style={{
            background: 'none', border: 'none',
            color: '#ccc', fontSize: 15, lineHeight: 1,
            cursor: 'pointer', padding: 0,
          }}>✕</button>
        </div>
      </div>

      {hasOptions && (
        <div style={{
          marginTop: 8, padding: '7px 10px',
          background: '#f8f8f8', borderRadius: 8,
        }}>
          {item.exclusion && item.exclusion !== '없음' && (
            <SubRow label={item.exclusion} extra={0} />
          )}
          {item.side  && <SubRow label={item.side}  extra={item.sideExtra}  />}
          {item.drink && <SubRow label={item.drink} extra={item.drinkExtra} />}
        </div>
      )}
    </div>
  )
}

function SubRow({ label, extra }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between',
      fontSize: 11, color: '#777', marginBottom: 2,
    }}>
      <span>-{label}</span>
      <span style={{ display: 'flex', gap: 16 }}>
        <span>1</span>
        <span style={{ color: extra > 0 ? '#d44' : '#aaa' }}>
          {extra > 0 ? `+${extra.toLocaleString()}` : '0'}
        </span>
      </span>
    </div>
  )
}

function SmallBtn({ label, onClick }) {
  return (
    <button onClick={onClick} style={{
      width: 22, height: 22, borderRadius: 4,
      border: '1px solid #ccc', background: '#fff',
      fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
      cursor: 'pointer', padding: 0,
    }}>{label}</button>
  )
}

function Header({ onBack }) {
  return (
    <div style={{
      background: '#744032', padding: '10px 16px',
      display: 'flex', alignItems: 'center', flexShrink: 0,
    }}>
      <button onClick={onBack} style={{
        background: 'none', border: 'none',
        color: '#F5B800', fontSize: 30, lineHeight: 1,
        padding: '0 10px 0 0', cursor: 'pointer',
      }}>‹</button>
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
        <Logo height={38} />
      </div>
      <div style={{ width: 40 }} />
    </div>
  )
}
