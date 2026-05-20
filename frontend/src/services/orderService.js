// ─────────────────────────────────────────────────────────────────
// 주문 서비스 — DB 연동 시 이 파일만 수정하세요.
//
// POST /api/orders
//   Request  : { items, total, orderType, phone }
//   Response : { orderNum: number, orderId: string }
//
// GET /api/orders/:orderId
//   Response : { orderId, orderNum, status, createdAt }
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL

/**
 * 주문을 생성하고 주문번호를 반환합니다.
 * @param {{ items: object[], total: number, orderType: string|null, phone: string }} params
 * @returns {Promise<{ orderNum: number, orderId: string }>}
 */
export async function createOrder({ items, total, orderType, phone }) {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items, total, orderType, phone }),
    })
    if (!res.ok) throw new Error(`주문 생성 실패 (${res.status})`)
    return res.json() // { orderNum, orderId }
  }

  const orderNum = Math.floor(Math.random() * 999) + 1
  return { orderNum, orderId: `LOCAL-${Date.now()}` }
}

/**
 * 주문 상태를 조회합니다.
 * @param {string} orderId
 * @returns {Promise<{ orderId: string, orderNum: number, status: string, createdAt: string }>}
 */
export async function getOrderStatus(orderId) {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/orders/${orderId}`)
    if (!res.ok) throw new Error(`주문 조회 실패 (${res.status})`)
    return res.json()
  }
  return { orderId, status: 'completed', createdAt: new Date().toISOString() }
}
