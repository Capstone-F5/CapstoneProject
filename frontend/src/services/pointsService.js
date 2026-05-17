// ─────────────────────────────────────────────────────────────────
// 포인트/고객 서비스 — 회원 DB 연동 시 이 파일만 수정하세요.
//
// GET /api/points/lookup?phone={digits}
//   Response : { name: string, points: number }
//
// POST /api/points/add
//   Request  : { phone: string, amount: number, orderId: string }
//   Response : { success: boolean, newTotal: number }
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL

/**
 * 전화번호로 고객 정보를 조회합니다.
 * @param {string} phoneDigits - 숫자만 추출된 전화번호 (11자리)
 * @returns {Promise<{ name: string, points: number }>}
 */
export async function lookupCustomer(phoneDigits) {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/points/lookup?phone=${phoneDigits}`)
    if (!res.ok) throw new Error(`고객 조회 실패 (${res.status})`)
    return res.json() // { name, points }
  }
  return { name: '고객', points: 0 }
}

/**
 * 결제 완료 후 포인트를 적립합니다.
 * @param {{ phone: string, amount: number, orderId: string }} params
 * @returns {Promise<{ success: boolean, newTotal: number }>}
 */
export async function addPoints({ phone, amount, orderId }) {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/points/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, amount, orderId }),
    })
    if (!res.ok) throw new Error(`포인트 적립 실패 (${res.status})`)
    return res.json() // { success, newTotal }
  }
  return { success: true, newTotal: 0 }
}
