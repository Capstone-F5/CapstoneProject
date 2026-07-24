// ─────────────────────────────────────────────────────────────────
// GET /api/user/points/{phone} → UserPointsOut{ user_id, phone_number, name, current_points, tier }
// 포인트 적립은 별도 API 없이 POST /api/orders 생성 시 서버가 자동으로 처리한다.
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL

/**
 * 전화번호로 고객 정보를 조회한다. 미등록 회원(404)이어도 에러를 던지지 않고
 * registered:false 를 반환한다 — 결제는 그대로 진행되고, 주문 시 자동 회원가입된다.
 */
export async function lookupCustomer(phoneDigits) {
  const res = await fetch(`${API_BASE}/api/user/points/${phoneDigits}`)
  if (res.status === 404) return { name: null, points: null, tier: null, registered: false }
  if (!res.ok) throw new Error(`고객 조회 실패 (${res.status})`)
  const d = await res.json()
  return { name: d.name ?? null, points: d.current_points, tier: d.tier, registered: true }
}
