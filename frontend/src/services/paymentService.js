// ─────────────────────────────────────────────────────────────────
// POST /api/payments  Request: { order_id, method: CARD|SAMSUNG_PAY|QR_PAY|CASH, amount }
//                     Response: PaymentOut{ payment_id, order_id, method, amount, status, paid_at }
//
// method 매핑 근거: CartScreen.jsx 의 간편결제(네이버/카카오/제로/페이코) 버튼 4종이
// 전부 payPayment 대기화면(바코드/QR 일러스트)으로 수렴하므로 'pay' → QR_PAY 가 가장 근접.
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const METHOD_MAP = { card: 'CARD', cash: 'CASH', pay: 'QR_PAY' }

export async function processPayment({ orderId, method, amount }) {
  const res = await fetch(`${API_BASE}/api/payments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      order_id: orderId,
      method: METHOD_MAP[method] ?? 'CARD',
      amount,
    }),
  })
  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { /* ignore */ }
    throw new Error(detail || `결제 실패 (${res.status})`)
  }
  const d = await res.json()
  return { success: d.status === 'SUCCESS', paymentId: d.payment_id, status: d.status }
}
