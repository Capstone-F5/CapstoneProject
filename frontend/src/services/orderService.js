import { getSessionId } from './session'

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const ORDER_TYPE_MAP = { 'dine-in': 'EAT_IN', takeout: 'TAKE_OUT' }

async function safeDetail(res) {
  try { return (await res.json()).detail } catch { return null }
}

/**
 * 주문을 생성한다. 서버가 session_id 로 찾은 백엔드 카트(POST /api/cart/*)의
 * 내용을 그대로 주문으로 전환하므로 items 는 요청에 포함하지 않는다.
 */
export async function createOrder({ orderType, phone = null, couponCode = null, pointsToUse = 0 }) {
  const res = await fetch(`${API_BASE}/api/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: getSessionId(),
      order_type: ORDER_TYPE_MAP[orderType] ?? 'TAKE_OUT',
      phone: phone || null,
      points_to_use: pointsToUse || 0,
      coupon_code: couponCode || null,
    }),
  })
  if (!res.ok) throw new Error((await safeDetail(res)) || `주문 생성 실패 (${res.status})`)
  const d = await res.json()
  return {
    orderId: d.order_id,
    orderNum: d.order_number,
    finalAmount: Number(d.final_amount),
    discountAmount: Number(d.discount_amount),
    pointsEarned: d.points_earned,
  }
}

/**
 * 결제 진행 전 쿠폰 코드를 미리 검증한다 (주문 생성 없이 할인 금액만 미리 확인).
 */
export async function validateCoupon(code, subtotal) {
  const res = await fetch(`${API_BASE}/api/orders/validate-coupon?code=${encodeURIComponent(code)}&subtotal=${subtotal}`)
  if (!res.ok) {
    const message = (await safeDetail(res)) || `쿠폰 확인 실패 (${res.status})`
    return { valid: false, message }
  }
  const d = await res.json()
  return { valid: true, discountAmount: Number(d.discount_amount), finalAmount: Number(d.final_amount) }
}

export async function fetchActiveDiscounts() {
  try {
    const res = await fetch(`${API_BASE}/api/orders/active-discounts`)
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

export async function previewDiscount() {
  try {
    const res = await fetch(`${API_BASE}/api/orders/preview-discount?session_id=${getSessionId()}`)
    if (!res.ok) return { discountAmount: 0, applicable: [] }
    const d = await res.json()
    return { discountAmount: d.discount_amount, finalAmount: d.final_amount, applicable: d.applicable }
  } catch {
    return { discountAmount: 0, applicable: [] }
  }
}

export async function getOrderStatus(orderId) {
  const res = await fetch(`${API_BASE}/api/orders/${orderId}`)
  if (!res.ok) throw new Error(`주문 조회 실패 (${res.status})`)
  const d = await res.json()
  return { orderId: d.order_id, orderNum: d.order_number, status: d.status, createdAt: d.created_at }
}
