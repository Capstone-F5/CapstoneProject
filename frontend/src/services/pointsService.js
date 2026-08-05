// ─────────────────────────────────────────────────────────────────
// GET /api/user/points/{phone} → UserPointsOut{ user_id, phone_number, name, current_points, tier }
// POST /api/user/register     → 정식 회원가입 (별도 회원가입 화면 전용)
//
// 전화번호를 결제 시 한 번 입력했다고 회원가입이 되는 게 아니다 — 포인트는 전화번호 기준으로
// 자동 추적(비회원, is_guest=True)되지만, 정식 회원(is_guest=False)이 되려면 반드시
// /api/user/register 를 거쳐야 한다.
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL ?? ''

/**
 * 전화번호로 고객 정보를 조회한다. 미등록(404)이어도 에러를 던지지 않고 registered:false 를
 * 반환한다 — 결제는 그대로 진행되고, 정식 회원가입 여부와 무관하게 포인트만 자동 추적된다.
 */
export async function lookupCustomer(phoneDigits) {
  const res = await fetch(`${API_BASE}/api/user/points/${phoneDigits}`)
  if (res.status === 404) return { name: null, points: null, tier: null, registered: false }
  if (!res.ok) throw new Error(`고객 조회 실패 (${res.status})`)
  const d = await res.json()
  return { name: d.name ?? null, points: d.current_points, tier: d.tier, registered: true }
}

/**
 * 정식 회원가입(별도 회원가입 화면 전용). 이미 포인트 추적용 비회원 레코드가 있으면
 * 그대로 정식 회원으로 전환된다(포인트 유지).
 */
export async function registerCustomer(phoneDigits, name) {
  const res = await fetch(`${API_BASE}/api/user/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: phoneDigits, name: name || null }),
  })
  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { /* ignore */ }
    throw new Error(detail || `회원가입 실패 (${res.status})`)
  }
  const d = await res.json()
  return {
    userId: d.user_id,
    phone: d.phone_number,
    name: d.name,
    points: d.current_points,
    alreadyMember: d.already_member,
  }
}
