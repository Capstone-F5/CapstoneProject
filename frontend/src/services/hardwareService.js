// 카드리더/현금수납기 등 물리적 결제 장치 트리거 — 지금은 백엔드(api/hardware.py)가
// 시뮬레이션만 한다. 나중에 아두이노 등 실제 하드웨어를 연동할 때는 백엔드 내부 구현만
// 바꾸면 되고, 이 함수의 시그니처·호출부(CartScreen.jsx)는 그대로 유지된다.
const API_BASE = import.meta.env.VITE_API_URL

export async function triggerHardwareAction(action, orderId = null) {
  try {
    const res = await fetch(`${API_BASE}/api/hardware/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, order_id: orderId }),
    })
    if (!res.ok) throw new Error(`hardware trigger failed (${res.status})`)
    return await res.json()
  } catch (e) {
    // 하드웨어 트리거 실패가 결제 자체를 막지 않는다 — 나중에 실제 장치 연동 후에도
    // 하드웨어 오류 때문에 결제 흐름이 멈추지 않도록 방어적으로 처리.
    console.error('[hardwareService] 트리거 실패:', e)
    return { ok: false, simulated: true }
  }
}
