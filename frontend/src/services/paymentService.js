// ─────────────────────────────────────────────────────────────────
// 결제 서비스 — 결제 게이트웨이 연동 시 이 파일만 수정하세요.
//
// POST /api/payments
//   Request  : { method, amount, orderId, phone? }
//   Response : { success: boolean, transactionId: string }
//
// method 값: 'card' | 'cash' | 'pay'
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL

/**
 * 결제를 처리합니다.
 * @param {{ method: 'card'|'cash'|'pay', amount: number, orderId: string, phone?: string }} params
 * @returns {Promise<{ success: boolean, transactionId: string }>}
 */
export async function processPayment({ method, amount, orderId, phone }) {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/payments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method, amount, orderId, phone }),
    })
    if (!res.ok) throw new Error(`결제 처리 실패 (${res.status})`)
    return res.json() // { success, transactionId }
  }

  return { success: true, transactionId: `LOCAL-${Date.now()}` }
}
