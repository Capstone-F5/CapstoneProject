import { useState } from 'react'
import Logo from '../components/Logo'

const POINT_KEYS = ['1','2','3','4','5','6','7','8','9','지움','0','010']

const LIST_PX   = 16
const CARD_PX   = 16
const HDR_PX    = LIST_PX + CARD_PX
const COL_QTY   = 130
const COL_PRICE = 140
const IMG_SIZE  = 90

/* 실제 API 연동 시 이 함수만 교체하면 됩니다 */
async function fetchCustomerName(phoneDigits) {
  // TODO: const res = await fetch(`/api/points/lookup?phone=${phoneDigits}`)
  //       return (await res.json()).name
  return '고객'
}

export default function CartScreen({ cart, total, updateQty, clearCart, nav }) {
  const [showPointPrompt,  setShowPointPrompt]  = useState(false)
  const [showPointsPopup,  setShowPointsPopup]  = useState(false)
  const [showPaymentPopup, setShowPaymentPopup] = useState(false)
  const [showCardPayment,  setShowCardPayment]  = useState(false)
  const [showCashPayment,  setShowCashPayment]  = useState(false)
  const [showPayPayment,   setShowPayPayment]   = useState(false)
  const [pointsInput,      setPointsInput]      = useState('')
  const [pointsError,      setPointsError]      = useState('')
  const [confirmedPhone,   setConfirmedPhone]   = useState('')
  const [confirmedName,    setConfirmedName]    = useState('')

  const handlePayClick = () => {
    if (cart.length === 0) return
    setShowPointPrompt(true)
  }

  const handlePointKey = (key) => {
    if (key === '지움')               setPointsInput(p => p.slice(0, -1))
    else if (key === '010')           setPointsInput('010')
    else if (pointsInput.length < 11) setPointsInput(p => p + key)
    setPointsError('')
  }

  const formatPhone = (v) => {
    const d = v.replace(/\D/g, '').slice(0, 11)
    if (d.length <= 3) return d
    if (d.length <= 7) return `${d.slice(0,3)}-${d.slice(3)}`
    return `${d.slice(0,3)}-${d.slice(3,7)}-${d.slice(7)}`
  }

  const closePointsPopup = () => {
    setShowPointsPopup(false)
    setPointsInput('')
    setPointsError('')
  }

  const openPayment = (phone = '', name = '') => {
    setConfirmedPhone(phone)
    setConfirmedName(name)
    closePointsPopup()
    setShowPaymentPopup(true)
  }

  const handlePointsConfirm = async () => {
    const d = pointsInput.replace(/\D/g, '')
    if (!d.length)       { setPointsError('전화번호를 입력해 주세요'); return }
    if (d.length !== 11) { setPointsError('11자리 번호를 입력해 주세요'); return }
    const name = await fetchCustomerName(d)
    openPayment(formatPhone(pointsInput), name)
  }

  const goPayment = (dest) => {
    setShowPaymentPopup(false)
    if (dest === 'cardPayment') setShowCardPayment(true)
    else if (dest === 'cashPayment') setShowCashPayment(true)
    else if (dest === 'payPayment')  setShowPayPayment(true)
  }

  const handleComplete = () => {
    setShowCardPayment(false)
    setShowCashPayment(false)
    setShowPayPayment(false)
    clearCart()
    nav('start')
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      height: '100dvh', height: '100vh',
      overflow: 'hidden', background: '#f2f2f2',
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
        background: '#fff', padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid #eee', flexShrink: 0,
      }}>
        <span style={{ fontSize: 24, fontWeight: 900, color: '#1a1a1a' }}>주문내역</span>
        <button onClick={clearCart} style={{
          border: '1.5px solid #ccc', borderRadius: 8,
          background: '#fff', padding: '10px 20px',
          fontSize: 16, fontWeight: 600, color: '#555', cursor: 'pointer',
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
        borderBottom: '2px solid #eee', flexShrink: 0,
      }}>
        <span style={{ gridColumn: 1, textAlign: 'center' }}>메뉴</span>
        <span style={{ gridColumn: 3, textAlign: 'center' }}>수량</span>
        <span style={{ gridColumn: 4, textAlign: 'center' }}>금액</span>
      </div>

      {/* ── 아이템 목록 ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: `14px ${LIST_PX}px` }}>
        {cart.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#bbb', padding: '100px 0', fontSize: 20 }}>
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
        background: '#fff', borderTop: '2px solid #ddd',
        padding: '16px 20px', flexShrink: 0,
      }}>
        <div style={{
          display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline',
          gap: 14, marginBottom: 16,
        }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#555' }}>총 결제금액</span>
          <span style={{ fontSize: 34, fontWeight: 900, color: '#1a1a1a' }}>
            {total.toLocaleString()} 원
          </span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={() => setShowPointsPopup(true)} style={{
            flex: 1, padding: '22px 0', border: 'none', borderRadius: 12,
            background: '#d0d0d0', color: '#444', fontSize: 22, fontWeight: 700, cursor: 'pointer',
          }}>포인트</button>
          <button onClick={handlePayClick} disabled={cart.length === 0} style={{
            flex: 2, padding: '22px 0', border: 'none', borderRadius: 12,
            background: cart.length > 0 ? '#F5B800' : '#ccc',
            color: '#1a1a1a', fontSize: 22, fontWeight: 900,
            cursor: cart.length > 0 ? 'pointer' : 'default',
          }}>결제하기</button>
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
              onClick={() => { setShowPointPrompt(false); openPayment() }} />
            <ModalBtn label="예" color="#F5B800" textColor="#1a1a1a"
              onClick={() => { setShowPointPrompt(false); setShowPointsPopup(true) }} />
          </div>
        </ModalBase>
      )}

      {/* ── 전화번호 입력 팝업 ── */}
      {showPointsPopup && (
        <ModalBase onClose={closePointsPopup}>
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
            {formatPhone(pointsInput) || ' '}
          </div>
          {pointsError && (
            <p style={{ fontSize: 13, color: '#e44', textAlign: 'center', marginBottom: 8 }}>
              {pointsError}
            </p>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 16 }}>
            {POINT_KEYS.map(k => (
              <button key={k} onClick={() => handlePointKey(k)} style={{
                padding: '19px 0', background: '#9e9e9e', color: '#fff',
                border: 'none', borderRadius: 8, fontSize: 20, fontWeight: 700, cursor: 'pointer',
              }}>{k}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <ModalBtn label="취소" color="#d4d4d4" textColor="#555" onClick={closePointsPopup} />
            <ModalBtn label="확인" color="#F5B800" textColor="#1a1a1a" onClick={handlePointsConfirm} />
          </div>
        </ModalBase>
      )}

      {/* ── 결제 수단 선택 팝업 ── */}
      {showPaymentPopup && (
        <ModalBase onClose={() => setShowPaymentPopup(false)}>
          {/* 인사말 + 금액 */}
          <div style={{ marginBottom: 18 }}>
            {confirmedName && (
              <div style={{ fontSize: 18, fontWeight: 900, color: '#1a1a1a', marginBottom: 2 }}>
                안녕하세요,{' '}
                <span style={{ color: '#744032' }}>{confirmedName}</span>님
              </div>
            )}
            <div style={{ fontSize: 13, color: '#aaa', fontWeight: 600, marginBottom: 6 }}>
              결제 수단을 선택하세요
            </div>
            <div style={{ fontSize: 28, fontWeight: 900, color: '#744032' }}>
              {total.toLocaleString()}<span style={{ fontSize: 16, color: '#888', marginLeft: 4 }}>원</span>
            </div>
          </div>

          {/* 신용카드+삼성페이 | 현금 — 2×1 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
            <button onClick={() => goPayment('cardPayment')} style={{
              padding: '18px 12px', border: '1.5px solid #e8e8e8', borderRadius: 14, background: '#fff',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, cursor: 'pointer',
            }}>
              <div style={{ display: 'flex', gap: 6 }}>
                <PayBadge bg="linear-gradient(135deg,#1565C0,#42A5F5)" color="#fff">💳</PayBadge>
                <PayBadge bg="#1428A0" color="#fff" small>
                  <span style={{ fontSize: 8, fontWeight: 900, display: 'block', lineHeight: 1 }}>SAMSUNG</span>
                  <span style={{ fontSize: 11, fontWeight: 900 }}>Pay</span>
                </PayBadge>
              </div>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>신용카드 / 삼성페이</span>
            </button>

            <button onClick={() => goPayment('cashPayment')} style={{
              padding: '18px 12px', border: '1.5px solid #e8e8e8', borderRadius: 14, background: '#fff',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, cursor: 'pointer',
            }}>
              <PayBadge bg="#E8F5E9" color="#2e7d32">💵</PayBadge>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>현금</span>
            </button>
          </div>

          {/* 간편결제 */}
          <div style={{ fontSize: 12, color: '#888', fontWeight: 600, marginBottom: 10 }}>간편결제</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 18 }}>
            {[
              { logo: null, fallbackLabel: 'N Pay',  fallbackColor: '#03C75A', sub: '네이버페이' },
              { logo: null, fallbackLabel: '·pay',   fallbackColor: '#b8860b', sub: '카카오페이' },
              { logo: null, fallbackLabel: '0 pay',  fallbackColor: '#333',    sub: '제로페이'  },
              { logo: null, fallbackLabel: 'PAYCO',  fallbackColor: '#E2231A', sub: '페이코'    },
            ].map(p => (
              <button key={p.sub} onClick={() => goPayment('payPayment')} style={{
                padding: '16px 12px', border: '1.5px solid #e8e8e8', borderRadius: 12, background: '#fff',
                display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer',
              }}>
                {p.logo
                  ? <img src={p.logo} alt={p.sub} style={{ width: 36, height: 24, objectFit: 'contain', flexShrink: 0 }} />
                  : <span style={{ fontSize: 15, fontWeight: 900, color: p.fallbackColor, minWidth: 36, textAlign: 'center' }}>{p.fallbackLabel}</span>
                }
                <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{p.sub}</span>
              </button>
            ))}
          </div>

          <button onClick={() => setShowPaymentPopup(false)} style={{
            width: '100%', padding: '15px 0', border: 'none', borderRadius: 12,
            background: '#e8e8e8', color: '#666', fontSize: 16, fontWeight: 700, cursor: 'pointer',
          }}>취소</button>
        </ModalBase>
      )}

      {/* ── 카드 결제 대기 팝업 ── */}
      {showCardPayment && (
        <PayWaitPopup
          title="카드를 리더기에 읽혀주세요"
          total={total}
          onCancel={() => { setShowCardPayment(false); setShowPaymentPopup(true) }}
          onComplete={handleComplete}
        >
          <CardIllustration />
        </PayWaitPopup>
      )}

      {/* ── 현금 결제 대기 팝업 ── */}
      {showCashPayment && (
        <PayWaitPopup
          title="현금을 투입해주세요"
          total={total}
          onCancel={() => { setShowCashPayment(false); setShowPaymentPopup(true) }}
        >
          <CashIllustration />
        </PayWaitPopup>
      )}

      {/* ── 간편결제 대기 팝업 ── */}
      {showPayPayment && (
        <PayWaitPopup
          title="바코드를 스캔해 주세요"
          total={total}
          onCancel={() => { setShowPayPayment(false); setShowPaymentPopup(true) }}
        >
          <BarcodeIllustration />
        </PayWaitPopup>
      )}
    </div>
  )
}

/* ── 결제 대기 팝업 ── */
function PayWaitPopup({ title, total, onCancel, onComplete, children }) {
  return (
    <ModalBase onClose={onCancel}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 20, fontWeight: 900, marginBottom: 20, lineHeight: 1.4 }}>
          {title}
        </div>

        <div style={{
          background: '#616161', borderRadius: 8,
          padding: '14px 20px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: 28,
        }}>
          <span style={{ color: '#ccc', fontSize: 14 }}>결제할 금액</span>
          <span style={{ color: '#F5B800', fontSize: 22, fontWeight: 900 }}>
            {(total || 0).toLocaleString()} 원
          </span>
        </div>

        <div style={{ marginBottom: 28 }}>{children}</div>

        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={onCancel} style={{
            flex: 1, padding: '14px 0', borderRadius: 12,
            border: 'none', background: '#e0e0e0', color: '#555',
            fontSize: 16, fontWeight: 700, cursor: 'pointer',
          }}>취소</button>
          {onComplete && (
            <button onClick={onComplete} style={{
              flex: 1, padding: '14px 0', borderRadius: 12,
              border: 'none', background: '#F5B800', color: '#1a1a1a',
              fontSize: 16, fontWeight: 700, cursor: 'pointer',
            }}>완료</button>
          )}
        </div>
      </div>
    </ModalBase>
  )
}

/* ── 일러스트: 카드 ── */
function CardIllustration() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
      <div style={{
        width: 72, height: 96, background: '#bdbdbd', borderRadius: 8,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'flex-start', paddingTop: 10, position: 'relative',
      }}>
        <div style={{ width: 36, height: 4, background: '#888', borderRadius: 2, marginBottom: 4 }} />
        <div style={{ fontSize: 8, color: '#fff', fontWeight: 700, letterSpacing: 0.5 }}>IC CARD</div>
        <div style={{ position: 'absolute', bottom: 28, width: 40, height: 4, background: '#555', borderRadius: 2 }} />
        <div style={{ position: 'absolute', bottom: 8, width: 24, height: 24, borderRadius: '50%', background: '#999' }} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{
          width: 68, height: 44, borderRadius: 6,
          background: 'linear-gradient(135deg,#F5B800,#E6A700)',
          boxShadow: '0 3px 10px rgba(0,0,0,0.2)', position: 'relative', flexShrink: 0,
        }}>
          <div style={{ position: 'absolute', left: 6, top: 8, width: 20, height: 14, borderRadius: 3, border: '1.5px solid rgba(255,255,255,0.6)' }} />
          <div style={{ position: 'absolute', right: 6, bottom: 8, display: 'flex', gap: 3 }}>
            {[0,1,2,3].map(i => <div key={i} style={{ width: 5, height: 5, borderRadius: '50%', background: 'rgba(255,255,255,0.5)' }} />)}
          </div>
        </div>
        <div style={{ fontSize: 40, marginLeft: -4 }}>✋</div>
      </div>
    </div>
  )
}

/* ── 일러스트: 현금 ── */
function CashIllustration() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'relative' }}>
        <div style={{
          width: 90, height: 110, borderRadius: 10, background: '#bdbdbd',
          display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 14, gap: 6,
        }}>
          <div style={{ width: 50, height: 6, background: '#757575', borderRadius: 3 }} />
          <div style={{ width: 50, height: 3, background: '#9e9e9e', borderRadius: 2 }} />
          <div style={{ width: 50, height: 3, background: '#9e9e9e', borderRadius: 2 }} />
          <div style={{ width: 60, height: 40, border: '2px solid #9e9e9e', borderRadius: 6, marginTop: 4, background: '#d0d0d0' }} />
        </div>
        <div style={{ position: 'absolute', bottom: 20, right: -52 }}>
          <div style={{
            width: 68, height: 34, borderRadius: 4,
            background: 'linear-gradient(135deg,#66BB6A,#43A047)',
            boxShadow: '1px 2px 6px rgba(0,0,0,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
          }}>
            {[0,1].map(i => <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', border: '1.5px solid rgba(255,255,255,0.5)' }} />)}
          </div>
          <div style={{ fontSize: 28, textAlign: 'center', marginTop: 2 }}>✋</div>
        </div>
      </div>
    </div>
  )
}

/* ── 일러스트: 바코드 ── */
function BarcodeIllustration() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 24 }}>
      <div style={{ position: 'relative' }}>
        <div style={{
          width: 72, height: 110, borderRadius: 10, border: '3px solid #bbb', background: '#f5f5f5',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          padding: 8, overflow: 'hidden',
        }}>
          <div style={{ fontSize: 8, color: '#aaa', marginBottom: 4 }}>10:00</div>
          <div style={{ display: 'flex', gap: 1, alignItems: 'flex-end', height: 40 }}>
            {[3,5,2,4,3,5,2,4,3,5,2,4,3,5,2,4].map((h, i) => (
              <div key={i} style={{ width: 2, height: h * 6, background: '#222' }} />
            ))}
          </div>
          <div style={{ fontSize: 7, color: '#555', marginTop: 3, letterSpacing: 0.5 }}>1234567890</div>
          <div style={{ position: 'absolute', left: 8, right: 8, top: '52%', height: 1.5, background: '#f00', opacity: 0.8 }} />
        </div>
        <div style={{ textAlign: 'center', fontSize: 30, marginTop: -4 }}>✊</div>
      </div>
      <div style={{
        width: 64, height: 64, borderRadius: 8, background: '#424242',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{ width: 24, height: 24, borderRadius: '50%', background: '#ef5350', boxShadow: '0 0 8px rgba(239,83,80,0.6)' }} />
      </div>
    </div>
  )
}

/* ── CartItem ── */
function CartItem({ item, onUpdateQty }) {
  const hasOptions = (item.exclusion && item.exclusion !== '없음') || item.side || item.drink
  return (
    <div style={{
      background: '#fff', borderRadius: 14, marginBottom: 12,
      padding: `14px ${CARD_PX}px`, boxShadow: '0 1px 6px rgba(0,0,0,0.07)',
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: `${IMG_SIZE}px 1fr ${COL_QTY}px ${COL_PRICE}px`,
        columnGap: 12, rowGap: 10,
      }}>
        <div style={{
          gridColumn: 1, gridRow: '1 / 3',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 6,
        }}>
          {item.image
            ? <img src={item.image} alt={item.name} style={{ width: IMG_SIZE, height: IMG_SIZE, borderRadius: 10, objectFit: 'cover', display: 'block' }} />
            : <span style={{ fontSize: 44 }}>🍔</span>
          }
          <span style={{ fontSize: 14, fontWeight: 700, color: '#333', wordBreak: 'keep-all', textAlign: 'center', width: IMG_SIZE }}>
            {item.name}{item.type === 'set' ? ' 세트' : ''}
          </span>
        </div>

        <div style={{
          gridColumn: 3, gridRow: hasOptions ? 1 : '1 / 3',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          alignSelf: 'center',
        }}>
          <QtyBtn label="−" onClick={() => onUpdateQty(item.cartId, item.qty - 1)} />
          <span style={{ fontSize: 20, fontWeight: 700, minWidth: 22, textAlign: 'center' }}>{item.qty}</span>
          <QtyBtn label="+" onClick={() => onUpdateQty(item.cartId, item.qty + 1)} />
        </div>

        <div style={{
          gridColumn: 4, gridRow: hasOptions ? 1 : '1 / 3',
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8,
          alignSelf: 'center',
        }}>
          <span style={{ fontSize: 18, fontWeight: 800 }}>{(item.unitPrice * item.qty).toLocaleString()}원</span>
          <button onClick={() => onUpdateQty(item.cartId, 0)} style={{
            background: 'none', border: 'none', color: '#bbb',
            fontSize: 20, lineHeight: 1, cursor: 'pointer', padding: 0, flexShrink: 0,
          }}>✕</button>
        </div>

        {hasOptions && (
          <div style={{
            gridColumn: '2 / -1', gridRow: 2, background: '#ededed',
            borderRadius: 10, overflow: 'hidden', alignSelf: 'center', marginTop: 4,
          }}>
            {item.exclusion && item.exclusion !== '없음' && <SubRow label={item.exclusion} extra={0} />}
            {item.side  && <SubRow label={item.side}  extra={item.sideExtra}  />}
            {item.drink && <SubRow label={item.drink} extra={item.drinkExtra} />}
          </div>
        )}
      </div>
    </div>
  )
}

function SubRow({ label, extra }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `1fr ${COL_QTY}px ${COL_PRICE}px`,
      columnGap: 12, alignItems: 'center',
      padding: '11px 0 11px 14px', fontSize: 15, color: '#555',
      borderBottom: '1px solid rgba(0,0,0,0.06)',
    }}>
      <span style={{ fontWeight: 500 }}>- {label}</span>
      <span style={{ textAlign: 'center', fontWeight: 600 }}>1</span>
      <span style={{ textAlign: 'right', fontWeight: 600, paddingRight: 26, color: extra > 0 ? '#cc3333' : '#999' }}>
        {extra > 0 ? `+${extra.toLocaleString()}원` : '0'}
      </span>
    </div>
  )
}

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

function PayBadge({ bg, color, small, children }) {
  return (
    <div style={{
      width: 54, height: 36, borderRadius: 6, background: bg,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      color, fontSize: small ? undefined : 18,
    }}>
      {children}
    </div>
  )
}

function ModalBtn({ label, color, textColor, onClick }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: '14px 0', border: 'none', borderRadius: 10,
      background: color, color: textColor, fontSize: 18, fontWeight: 700, cursor: 'pointer',
    }}>{label}</button>
  )
}

function ModalBase({ onClose, children }) {
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 120,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '0 clamp(16px,5vw,24px)',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: '94%', maxWidth: 640,
        background: '#fff', borderRadius: 18,
        padding: 'clamp(22px,5vw,28px)',
        boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
      }}>
        {children}
      </div>
    </div>
  )
}
