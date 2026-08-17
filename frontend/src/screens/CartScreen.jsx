import { useState, useEffect, useRef, useMemo } from 'react'
import Logo from '../components/Logo'
import { lookupCustomer } from '../services/pointsService'
import { createOrder, validateCoupon, previewDiscount } from '../services/orderService'
import { processPayment } from '../services/paymentService'
import { triggerHardwareAction } from '../services/hardwareService'
import IdleOverlay from '../components/IdleOverlay'
import CouponScanModal from '../components/CouponScanModal'
import CameraPreview from '../components/CameraPreview'
import useT from '../i18n/useT'
import { useLocale } from '../i18n/LocaleContext'
import { SET_SIDES, SET_DRINKS } from '../data/menuData'

const POINT_KEYS = ['1','2','3','4','5','6','7','8','9','지움','0','010']

function computeItemDiscount(itemId, categoryId, unitPrice, activeDiscounts) {
  if (!activeDiscounts?.length) return null
  const today = new Date().toISOString().split('T')[0]
  let price = unitPrice
  for (const d of activeDiscounts) {
    if (!d.is_active) continue
    if (d.applicable_tier !== 'ALL') continue
    if (d.valid_from && today < d.valid_from) continue
    if (d.valid_until && today > d.valid_until) continue
    const matches =
      d.target_type === 'ALL' ||
      (d.target_type === 'MENU' && d.menu_item_id === itemId) ||
      (d.target_type === 'CATEGORY' && d.category_id === categoryId)
    if (!matches) continue
    if (d.discount_type === 'PERCENT') price = Math.round(price * (1 - Number(d.discount_value) / 100))
    else price = Math.max(0, price - Number(d.discount_value))
  }
  if (price === unitPrice) return null
  return { discountedPrice: price, savings: unitPrice - price }
}

// 결제 수단 이미지 경로 — null 이면 기존 이모티콘/텍스트 폴백 표시
// 예: card: '/assets/payment/card.png'
const PAYMENT_IMAGES = {
  card:     null, // 신용카드 / 삼성페이
  cash:     null, // 현금
  naver:    null, // 네이버페이
  kakao:    null, // 카카오페이
  zero:     null, // 제로페이
  payco:    null, // 페이코
  cardWait: null, // 카드 결제 대기 화면
  cashWait: null, // 현금 결제 대기 화면
  payWait:  null, // 간편결제 대기 화면
}

const LIST_PX   = 16
const CARD_PX   = 16
const HDR_PX    = LIST_PX + CARD_PX
const COL_QTY   = 130
const COL_PRICE = 140
const IMG_SIZE  = 90

export default function CartScreen({ cart, total, updateQty, clearCart, nav, setOrderNum, orderType, setOrderType, voiceRef, activeDiscounts = [] }) {
  const t = useT()
  const [showOrderTypeConfirm, setShowOrderTypeConfirm] = useState(false)
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
  const [confirmedRegistered, setConfirmedRegistered] = useState(null)
  const [paymentMethod,    setPaymentMethod]    = useState(null)
  const [couponCode,       setCouponCode]       = useState('')
  const [paymentError,     setPaymentError]     = useState('')
  const [emptyCartNotice,  setEmptyCartNotice]  = useState(false)
  const [couponInfo,       setCouponInfo]       = useState(null)   // { valid, message, discountAmount? }
  const [couponChecking,   setCouponChecking]   = useState(false)
  const [showCouponScan,   setShowCouponScan]   = useState(false)
  const [discountPreview,  setDiscountPreview]  = useState(null)  // { discountAmount, applicable }

  const isCompletingRef = useRef(false)

  const handlePayClick = () => {
    if (cart.length === 0) {
      setEmptyCartNotice(true)
      setTimeout(() => setEmptyCartNotice(false), 2000)
      return
    }
    setShowOrderTypeConfirm(true)
  }

  // 음성으로 "결제할게"를 말했을 때 진입 지점 — 매장/포장 재확인 팝업은 손으로 카드를 다시
  // 눌러 바꾸는 터치 전용 UI라 음성으로는 응답할 방법이 없다(order_type ui_action은 전역
  // 핸들러가 항상 menu 화면으로 이동시켜버려 결제 중간에 재사용할 수 없음, App.jsx 참고).
  // 주문 유형은 이미 대화로 확인했으므로, 음성 결제 시작은 이 팝업을 띄우지 않고 터치 사용자가
  // "확인"을 눌렀을 때와 동일한 다음 단계(포인트 질문)로 곧장 진행한다.
  const voiceStartCheckout = () => {
    if (cart.length === 0) {
      setEmptyCartNotice(true)
      setTimeout(() => setEmptyCartNotice(false), 2000)
      return
    }
    setShowPointPrompt(true)
  }

  const confirmOrderType = () => {
    setShowOrderTypeConfirm(false)
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

  const openPayment = (phone = '', name = '', registered = null) => {
    setConfirmedPhone(phone)
    setConfirmedName(name)
    setConfirmedRegistered(registered)
    closePointsPopup()
    setShowPaymentPopup(true)
  }

  const handlePointsConfirm = async (phoneArg) => {
    // 음성 입력(phoneArg)이 있으면 우선 사용 — setState 비동기로 stale 읽는 문제 회피.
    // onClick 핸들러로 호출되면 이벤트 객체가 들어오므로 문자열일 때만 사용.
    const raw = (typeof phoneArg === 'string' ? phoneArg : null) ?? pointsInput
    const d = raw.replace(/\D/g, '')
    if (!d.length)       { setPointsError(t('phoneError1')); return }
    if (d.length !== 11) { setPointsError(t('phoneError2')); return }
    const { name, registered } = await lookupCustomer(d)
    openPayment(formatPhone(raw), name, registered)
  }

  const handleCheckCoupon = async (codeArg) => {
    const code = (typeof codeArg === 'string' ? codeArg : couponCode).trim()
    if (!code) return
    setCouponChecking(true)
    try {
      const result = await validateCoupon(code, total, confirmedPhone.replace(/\D/g, '') || null)
      setCouponInfo(result)
    } catch (err) {
      setCouponInfo({ valid: false, message: err.message || '쿠폰 확인에 실패했습니다' })
    } finally {
      setCouponChecking(false)
    }
  }

  // CouponScanModal에서 검증+확인 완료 후 호출됨 (code, validatedInfo)
  const handleCouponDetected = (code, info) => {
    setShowCouponScan(false)
    setCouponCode(code)
    if (info) {
      setCouponInfo(info)
    } else {
      handleCheckCoupon(code)
    }
  }

  const cancelCoupon = () => {
    setCouponCode('')
    setCouponInfo(null)
  }

  const goPayment = (dest) => {
    setShowPaymentPopup(false)
    setPaymentError('')
    const methodMap = { cardPayment: 'card', cashPayment: 'cash', payPayment: 'pay' }
    setPaymentMethod(methodMap[dest] ?? 'card')
    if (dest === 'cardPayment') {
      setShowCardPayment(true)
      // 카드/삼성페이 결제 대기 화면 진입 시 물리적 카드리더 동작 트리거(현재는 시뮬레이션).
      // ★ 아두이노 등 실제 장치 연동 확장 지점 — hardwareService.js 참고.
      triggerHardwareAction('card_payment')
    } else if (dest === 'cashPayment') {
      setShowCashPayment(true)
      triggerHardwareAction('cash_payment')
    } else if (dest === 'payPayment') {
      setShowPayPayment(true)
    }
  }

  // 음성 화면 제어 브릿지 — App.jsx 큐가 호출. 처리 시 true 반환.
  useEffect(() => {
    if (!voiceRef) return
    voiceRef.current = (a) => {
      switch (a.type) {
        case 'start_checkout':
          voiceStartCheckout()
          return true
        case 'points':
          setShowPointPrompt(false)
          if (a.value === 'yes') setShowPointsPopup(true)
          else openPayment()
          return true
        case 'points_phone':
          setShowPointsPopup(true)
          setPointsInput(a.phone ?? '')
          handlePointsConfirm(a.phone ?? '')
          return true
        case 'payment_method': {
          const destMap = { card: 'cardPayment', cash: 'cashPayment', pay: 'payPayment' }
          const dest = destMap[a.value]
          if (!dest) return false
          goPayment(dest)
          return true
        }
        default:
          return false
      }
    }
    return () => { if (voiceRef) voiceRef.current = null }
  }, [voiceRef, cart, total])  // eslint-disable-line react-hooks/exhaustive-deps

  // 카트가 바뀔 때마다 적용 가능한 할인 미리보기
  useEffect(() => {
    if (cart.length === 0) { setDiscountPreview(null); return }
    previewDiscount().then(r => setDiscountPreview(r.discountAmount > 0 ? r : null))
  }, [cart])

  const automaticDiscount = discountPreview?.discountAmount ?? 0
  const couponDiscount = couponInfo?.valid ? (couponInfo.discountAmount ?? 0) : 0
  const finalDisplayAmount = Math.max(0, total - automaticDiscount - couponDiscount)

  const handleComplete = async () => {
    if (isCompletingRef.current) return
    isCompletingRef.current = true
    setPaymentError('')
    try {
      const { orderId, orderNum, finalAmount: serverFinalAmount } = await createOrder({
        orderType,
        phone: confirmedPhone.replace(/\D/g, '') || null,
        couponCode: couponCode.trim() || null,
      })
      // 서버가 반환한 finalAmount 사용 (쿠폰 + Discount 테이블 할인 모두 반영됨)
      const payAmount = serverFinalAmount ?? 0
      // 결제 금액이 0원이면 결제 API 호출 없이 완료 처리
      if (payAmount > 0) {
        const { success } = await processPayment({ orderId, method: paymentMethod, amount: payAmount })
        if (!success) throw new Error('결제가 승인되지 않았습니다')
      }
      setShowCardPayment(false)
      setShowCashPayment(false)
      setShowPayPayment(false)
      setOrderNum(orderNum)
      clearCart()
      nav('complete')
    } catch (err) {
      console.error('결제 중 오류:', err)
      setPaymentError(err.message || '결제 처리 중 오류가 발생했습니다. 다시 시도해 주세요.')
      isCompletingRef.current = false
    }
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      height: '100%',
      overflow: 'hidden', background: '#f2f2f2',
    }}>

      {/* ── 헤더 ── */}
      <div style={{
        background: '#744032', padding: '20px 32px',
        display: 'flex', alignItems: 'center', flexShrink: 0,
      }}>
        <button onClick={() => nav('menu')} style={{
          background: 'none', border: 'none',
          color: '#F5B800', fontSize: 60, lineHeight: 1,
          padding: '0 16px 0 0', cursor: 'pointer',
        }}>‹</button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <Logo height={76} />
        </div>
        <div style={{ width: 80 }} />
      </div>

      {/* ── 주문내역 타이틀 ── */}
      <div style={{
        background: '#fff', padding: '16px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid #eee', flexShrink: 0,
      }}>
        <span style={{ fontSize: 24, fontWeight: 900, color: '#1a1a1a' }}>{t('orderHistory')}</span>
        <button onClick={clearCart} style={{
          border: '1.5px solid #ccc', borderRadius: 8,
          background: '#fff', padding: '10px 20px',
          fontSize: 16, fontWeight: 600, color: '#555', cursor: 'pointer',
        }}>{t('clearAll')}</button>
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
        <span style={{ gridColumn: 1, textAlign: 'center' }}>{t('colMenu')}</span>
        <span style={{ gridColumn: 3, textAlign: 'center' }}>{t('colQty')}</span>
        <span style={{ gridColumn: 4, textAlign: 'center' }}>{t('colPrice')}</span>
      </div>

      {/* ── 아이템 목록 ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: `14px ${LIST_PX}px` }}>
        {cart.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#bbb', padding: '100px 0', fontSize: 20 }}>
            {t('cartEmpty')}
          </div>
        ) : (
          cart.map(item => {
            const disc = computeItemDiscount(item.id, item.categoryId ?? null, item.unitPrice, activeDiscounts)
            return (
              <CartItem
                key={item.cartId}
                item={item}
                onUpdateQty={updateQty}
                discountedUnitPrice={disc ? disc.discountedPrice : null}
              />
            )
          })
        )}
      </div>

      {/* ── 하단: 합계 + 버튼 ── */}
      <div style={{
        background: '#fff', borderTop: '2px solid #ddd',
        padding: '16px 20px', flexShrink: 0,
      }}>
        {discountPreview && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: 14, color: '#e44', fontWeight: 600 }}>
              할인 -{discountPreview.discountAmount.toLocaleString('ko-KR')}원
            </span>
            <span style={{ fontSize: 12, color: '#aaa' }}>
              ({discountPreview.applicable.map(a => a.name).join(', ')})
            </span>
          </div>
        )}
        {couponInfo?.valid && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
            <span style={{ fontSize: 14, color: '#e44', fontWeight: 600 }}>
              쿠폰 -{(couponInfo.discountAmount ?? 0).toLocaleString('ko-KR')}원
            </span>
            <button onClick={cancelCoupon} style={{ marginLeft: 8, border: 'none', background: 'none', color: '#777', textDecoration: 'underline', cursor: 'pointer' }}>
              쿠폰 취소
            </button>
          </div>
        )}
        <div style={{
          display: 'flex', justifyContent: 'flex-end', alignItems: 'baseline',
          gap: 14, marginBottom: 16,
        }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#555' }}>{t('totalAmount')}</span>
          <span style={{ fontSize: 34, fontWeight: 900, color: '#1a1a1a' }}>
            {finalDisplayAmount.toLocaleString()} {t('won')}
          </span>
        </div>
        {emptyCartNotice && (
          <p style={{ textAlign: 'right', color: '#e44', fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
            장바구니가 비어있습니다
          </p>
        )}
        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={() => setShowPointsPopup(true)} style={{
            flex: 1, padding: '22px 0', border: 'none', borderRadius: 12,
            background: '#d0d0d0', color: '#444', fontSize: 22, fontWeight: 700, cursor: 'pointer',
          }}>{t('points')}</button>
          <button onClick={handlePayClick} style={{
            flex: 2, padding: '22px 0', border: 'none', borderRadius: 12,
            background: cart.length > 0 ? '#F5B800' : '#ccc',
            color: '#1a1a1a', fontSize: 22, fontWeight: 900,
            cursor: cart.length > 0 ? 'pointer' : 'default',
          }}>{t('checkout')}</button>
        </div>
      </div>

      {/* ── 매장/포장 재확인 팝업 ── */}
      {showOrderTypeConfirm && (
        <ModalBase onClose={() => setShowOrderTypeConfirm(false)}>
          <p style={{ fontSize: 20, fontWeight: 900, textAlign: 'center', marginBottom: 20 }}>
            주문 유형을 확인해 주세요
          </p>
          <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
            <OrderTypeChip
              label={t('dineIn')}
              image="/images/sets/F버거 세트.webp"
              active={orderType === 'dine-in'}
              onClick={() => setOrderType('dine-in')}
            />
            <OrderTypeChip
              label={t('takeout')}
              image="/images/etc/Takeout.webp"
              active={orderType === 'takeout'}
              onClick={() => setOrderType('takeout')}
            />
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <ModalBtn label={t('cancel')} color="#d4d4d4" textColor="#555"
              onClick={() => setShowOrderTypeConfirm(false)} />
            <ModalBtn label={t('confirm')} color="#F5B800" textColor="#1a1a1a"
              onClick={confirmOrderType} />
          </div>
        </ModalBase>
      )}

      {/* ── 포인트 적립 확인 팝업 ── */}
      {showPointPrompt && (
        <ModalBase onClose={() => setShowPointPrompt(false)}>
          <p style={{ fontSize: 22, fontWeight: 900, textAlign: 'center', marginBottom: 20 }}>
            {t('earnPoints')}
          </p>
          <div style={{ display: 'flex', gap: 12 }}>
            <ModalBtn label={t('no')} color="#d4d4d4" textColor="#555"
              onClick={() => { setShowPointPrompt(false); openPayment() }} />
            <ModalBtn label={t('yes')} color="#F5B800" textColor="#1a1a1a"
              onClick={() => { setShowPointPrompt(false); setShowPointsPopup(true) }} />
          </div>
        </ModalBase>
      )}

      {/* ── 전화번호 입력 팝업 ── */}
      {showPointsPopup && (
        <ModalBase onClose={closePointsPopup}>
          <p style={{ fontSize: 22, fontWeight: 900, textAlign: 'center', marginBottom: 4 }}>
            {t('enterPhone')}
          </p>
          <p style={{ fontSize: 15, color: '#666', textAlign: 'center', marginBottom: 14 }}>
            {t('enterPhoneSub')}
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
                padding: '25px 0', background: '#9e9e9e', color: '#fff',
                border: 'none', borderRadius: 8, fontSize: 20, fontWeight: 700, cursor: 'pointer',
              }}>{k}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <ModalBtn label={t('cancel')} color="#d4d4d4" textColor="#555" onClick={closePointsPopup} />
            <ModalBtn label={t('confirm')} color="#F5B800" textColor="#1a1a1a" onClick={handlePointsConfirm} />
          </div>
        </ModalBase>
      )}

      {/* ── 결제 수단 선택 팝업 ── */}
      {showPaymentPopup && (
        <ModalBase onClose={() => setShowPaymentPopup(false)} minHeight="clamp(500px,76vh,700px)">
          {/* 인사말 + 금액 — 회원+이름 / 회원인데 이름없음 / 미회원(주문 시 자동 임시 등록) 3가지 상태 표시 */}
          <div style={{ marginBottom: 28 }}>
            {confirmedRegistered !== null && (
              <div style={{ fontSize: 18, fontWeight: 900, color: '#1a1a1a', marginBottom: 2 }}>
                안녕하세요,{' '}
                <span style={{ color: '#744032' }}>
                  {confirmedRegistered
                    ? (confirmedName || '이름없음')
                    : '고객님(미가입)'}
                </span>
                {confirmedRegistered ? '님' : ''}
              </div>
            )}
            <div style={{ fontSize: 13, color: '#aaa', fontWeight: 600, marginBottom: 6 }}>
              {t('selectPayMethod')}
            </div>
            {finalDisplayAmount < total && (
              <div style={{ fontSize: 15, color: '#aaa', textDecoration: 'line-through', marginBottom: 2 }}>
                {total.toLocaleString()} {t('won')}
              </div>
            )}
            {automaticDiscount > 0 && (
              <div style={{ fontSize: 14, color: '#e44', fontWeight: 700, marginBottom: 2 }}>
                상품 할인 −{automaticDiscount.toLocaleString()} {t('won')}
              </div>
            )}
            {couponDiscount > 0 && (
              <div style={{ fontSize: 14, color: '#e44', fontWeight: 700, marginBottom: 2 }}>
                쿠폰 할인 −{couponDiscount.toLocaleString()} {t('won')}
              </div>
            )}
            <div style={{ fontSize: 28, fontWeight: 900, color: '#744032' }}>
              {finalDisplayAmount.toLocaleString()}<span style={{ fontSize: 16, color: '#888', marginLeft: 4 }}>{t('won')}</span>
            </div>
          </div>

          {/* 쿠폰 (선택) — QR/바코드 스캔 또는 수동 입력, 결제 전에 미리 검증해 할인 금액을 보여준다 */}
          <button
            onClick={() => { setCouponInfo(null); setShowCouponScan(true) }}
            disabled={couponChecking}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              width: '100%', boxSizing: 'border-box', border: '1.5px solid #e0e0e0',
              borderRadius: 10, padding: '12px 14px', fontSize: 15, fontWeight: 700,
              background: '#fafafa', color: '#744032', cursor: 'pointer', marginBottom: 6,
            }}
          >
            📷 {couponChecking ? '쿠폰 확인 중…' : couponCode ? `쿠폰 "${couponCode}" 적용됨 · 다시 스캔` : '쿠폰 QR·바코드 스캔 / 직접 입력'}
          </button>
          {couponInfo && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 0, marginBottom: 18 }}>
              <p style={{ fontSize: 13, fontWeight: 700, margin: 0, color: couponInfo.valid ? '#2e7d32' : '#e44' }}>
                {couponInfo.valid
                  ? `${couponInfo.discountAmount.toLocaleString()}원 쿠폰 할인 적용됩니다 (최종 결제 예정 ${finalDisplayAmount.toLocaleString()}원)`
                  : couponInfo.message}
              </p>
              {couponInfo.valid && (
                <button onClick={cancelCoupon} style={{ flexShrink: 0, border: 'none', background: 'none', color: '#777', textDecoration: 'underline', cursor: 'pointer' }}>
                  쿠폰 취소
                </button>
              )}
            </div>
          )}
          {!couponInfo && <div style={{ marginBottom: 18 }} />}

          {/* 신용카드+삼성페이 | 현금 — 2×1 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 18 }}>
            <button onClick={() => goPayment('cardPayment')} style={{
              padding: '32px 12px', border: '1.5px solid #e8e8e8', borderRadius: 14, background: '#fff',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, cursor: 'pointer',
            }}>
              {PAYMENT_IMAGES.card
                ? <img src={PAYMENT_IMAGES.card} alt="신용카드 / 삼성페이"
                    style={{ width: 96, height: 60, objectFit: 'contain' }} />
                : <div style={{ display: 'flex', gap: 6 }}>
                    <PayBadge bg="linear-gradient(135deg,#1565C0,#42A5F5)" color="#fff">💳</PayBadge>
                    <PayBadge bg="#1428A0" color="#fff" small>
                      <span style={{ fontSize: 8, fontWeight: 900, display: 'block', lineHeight: 1 }}>SAMSUNG</span>
                      <span style={{ fontSize: 11, fontWeight: 900 }}>Pay</span>
                    </PayBadge>
                  </div>
              }
              <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{t('creditCard')}</span>
            </button>

            <button onClick={() => goPayment('cashPayment')} style={{
              padding: '32px 12px', border: '1.5px solid #e8e8e8', borderRadius: 14, background: '#fff',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, cursor: 'pointer',
            }}>
              {PAYMENT_IMAGES.cash
                ? <img src={PAYMENT_IMAGES.cash} alt="현금"
                    style={{ width: 96, height: 60, objectFit: 'contain' }} />
                : <PayBadge bg="#E8F5E9" color="#2e7d32">💵</PayBadge>
              }
              <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{t('cash')}</span>
            </button>
          </div>

          {/* 간편결제 */}
          <div style={{ fontSize: 12, color: '#888', fontWeight: 600, marginBottom: 14 }}>{t('easyPay')}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 26 }}>
            {[
              { logo: PAYMENT_IMAGES.naver, fallbackLabel: 'N Pay', fallbackColor: '#03C75A', labelKey: 'naverPay' },
              { logo: PAYMENT_IMAGES.kakao, fallbackLabel: '·pay',  fallbackColor: '#b8860b', labelKey: 'kakaoPay' },
              { logo: PAYMENT_IMAGES.zero,  fallbackLabel: '0 pay', fallbackColor: '#333',    labelKey: 'zeroPay'  },
              { logo: PAYMENT_IMAGES.payco, fallbackLabel: 'PAYCO', fallbackColor: '#E2231A', labelKey: 'payco'    },
            ].map(p => (
              <button key={p.labelKey} onClick={() => goPayment('payPayment')} style={{
                padding: '26px 12px', border: '1.5px solid #e8e8e8', borderRadius: 12, background: '#fff',
                display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer',
              }}>
                {p.logo
                  ? <img src={p.logo} alt={t(p.labelKey)} style={{ width: 52, height: 34, objectFit: 'contain', flexShrink: 0 }} />
                  : <span style={{ fontSize: 15, fontWeight: 900, color: p.fallbackColor, minWidth: 52, textAlign: 'center' }}>{p.fallbackLabel}</span>
                }
                <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{t(p.labelKey)}</span>
              </button>
            ))}
          </div>

          <button onClick={() => setShowPaymentPopup(false)} style={{
            width: '100%', padding: '20px 0', border: 'none', borderRadius: 12,
            background: '#e8e8e8', color: '#666', fontSize: 16, fontWeight: 700, cursor: 'pointer',
          }}>{t('cancel')}</button>
        </ModalBase>
      )}

      {/* ── 카드 결제 대기 팝업 ── */}
      {showCardPayment && (
        <PayWaitPopup
          title={t('waitCard')}
          total={finalDisplayAmount}
          image={PAYMENT_IMAGES.cardWait}
          onCancel={() => { setShowCardPayment(false); setShowPaymentPopup(true) }}
          onComplete={handleComplete}
          error={paymentError}
        >
          <CardIllustration />
        </PayWaitPopup>
      )}

      {/* ── 현금 결제 대기 팝업 ── */}
      {showCashPayment && (
        <PayWaitPopup
          title={t('waitCash')}
          total={finalDisplayAmount}
          image={PAYMENT_IMAGES.cashWait}
          onCancel={() => { setShowCashPayment(false); setShowPaymentPopup(true) }}
          onComplete={handleComplete}
          error={paymentError}
        >
          <CashIllustration />
        </PayWaitPopup>
      )}

      {/* ── 간편결제 대기 팝업 ── */}
      {showPayPayment && (
        <PayWaitPopup
          title={t('waitPay')}
          total={finalDisplayAmount}
          image={PAYMENT_IMAGES.payWait}
          onCancel={() => { setShowPayPayment(false); setShowPaymentPopup(true) }}
          onComplete={handleComplete}
          error={paymentError}
        >
          {/* 간편결제 QR/바코드 인식을 흉내내기 위해 실제 카메라를 켠다(결제 자체는 시뮬레이션) */}
          <div style={{ position: 'relative', width: '100%', maxWidth: 240, aspectRatio: '1 / 1' }}>
            <CameraPreview style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 12 }} />
            <div style={{
              position: 'absolute', inset: '12%', border: '3px solid #F5B800',
              borderRadius: 10, pointerEvents: 'none',
            }} />
          </div>
        </PayWaitPopup>
      )}

      {showCouponScan && (
        <CouponScanModal
          onDetect={handleCouponDetected}
          onClose={() => setShowCouponScan(false)}
          total={total}
          phone={confirmedPhone.replace(/\D/g, '') || null}
        />
      )}

      <IdleOverlay onExpire={() => { clearCart(); nav('start') }} />
    </div>
  )
}

/* ── 결제 대기 팝업 ── */
function PayWaitPopup({ title, total, onCancel, onComplete, image, children, error }) {
  const t = useT()
  useEffect(() => {
    const timer = setTimeout(() => onComplete?.(), 5000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <ModalBase onClose={onCancel} minHeight="clamp(440px,66vh,600px)">
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', flex: 1, justifyContent: 'space-between' }}>
        <div style={{ fontSize: 20, fontWeight: 900, lineHeight: 1.4 }}>
          {title}
        </div>

        {error && (
          <div style={{
            background: '#fdecea', color: '#c62828', borderRadius: 8,
            padding: '10px 14px', fontSize: 14, fontWeight: 600,
          }}>{error}</div>
        )}

        <div style={{
          background: '#616161', borderRadius: 8,
          padding: '14px 20px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ color: '#ccc', fontSize: 14 }}>{t('payAmount')}</span>
          <span style={{ color: '#F5B800', fontSize: 22, fontWeight: 900 }}>
            {(total || 0).toLocaleString()} {t('won')}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {image
            ? <img src={image} alt="" style={{ width: '100%', maxWidth: 240, height: 'auto', objectFit: 'contain' }} />
            : children
          }
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={onCancel} style={{
            flex: 1, padding: '14px 0', borderRadius: 12,
            border: 'none', background: '#e0e0e0', color: '#555',
            fontSize: 16, fontWeight: 700, cursor: 'pointer',
          }}>{t('cancel')}</button>
          {onComplete && (
            <button onClick={onComplete} style={{
              flex: 1, padding: '14px 0', borderRadius: 12,
              border: 'none', background: '#F5B800', color: '#1a1a1a',
              fontSize: 16, fontWeight: 700, cursor: 'pointer',
            }}>{t('complete')}</button>
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

function translateOptionName(korName, locale) {
  if (!korName || locale === 'ko') return korName
  const all = [...SET_SIDES, ...SET_DRINKS]
  const found = all.find(x => x.name === korName)
  if (!found) return korName
  if (locale === 'ja') return found.nameJa ?? found.nameEn ?? korName
  if (locale === 'zh') return found.nameZh ?? found.nameEn ?? korName
  return found.nameEn ?? korName
}

/* ── CartItem ── */
function CartItem({ item, onUpdateQty, discountedUnitPrice }) {
  const t = useT()
  const { locale } = useLocale()
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
            {item.name}{item.type === 'set' ? ` ${t('set')}` : ''}
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
          {discountedUnitPrice != null && discountedUnitPrice < item.unitPrice ? (
            <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
              <span style={{ fontSize: 14, color: '#bbb', textDecoration: 'line-through', fontWeight: 400 }}>
                {(item.unitPrice * item.qty).toLocaleString()}{t('won')}
              </span>
              <span style={{ fontSize: 18, fontWeight: 800, color: '#e44' }}>
                {(discountedUnitPrice * item.qty).toLocaleString()}{t('won')}
              </span>
            </span>
          ) : (
            <span style={{ fontSize: 18, fontWeight: 800 }}>{(item.unitPrice * item.qty).toLocaleString()}{t('won')}</span>
          )}
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
            {item.side  && <SubRow label={translateOptionName(item.side,  locale)} extra={item.sideExtra}  />}
            {item.drink && <SubRow label={translateOptionName(item.drink, locale)} extra={item.drinkExtra} />}
          </div>
        )}
      </div>
    </div>
  )
}

function SubRow({ label, extra }) {
  const t = useT()
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
        {extra > 0 ? `+${extra.toLocaleString()}${t('won')}` : '0'}
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

function OrderTypeChip({ label, image, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: '14px 8px 12px', borderRadius: 14,
      border: active ? '2.5px solid #744032' : '1.5px solid #ddd',
      background: active ? '#fbf3f0' : '#fff',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
      cursor: 'pointer',
    }}>
      <img
        src={image}
        alt={label}
        style={{
          width: '100%', maxWidth: 120, aspectRatio: '1 / 1',
          objectFit: 'contain', borderRadius: 10,
        }}
      />
      <span style={{
        fontSize: 16, fontWeight: 800,
        color: active ? '#744032' : '#555',
      }}>{label}</span>
    </button>
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

function ModalBase({ onClose, children, minHeight }) {
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
        display: 'flex', flexDirection: 'column',
        ...(minHeight && { minHeight }),
      }}>
        {children}
      </div>
    </div>
  )
}
