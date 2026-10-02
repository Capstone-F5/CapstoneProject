import { getSessionId } from './session'

// 화면(터치 또는 빠른 응답)에서 끝낸 결제 단계를 서버에 알린다.
// 서버의 결제 진행 상태(checkout_progress)는 LLM이 도구를 호출할 때만 갱신되므로, 터치로 포인트 팝업에
// 답하면 서버는 모르는 채로 "포인트 적립하시겠어요?"를 다시 묻는다. 실패해도 주문 흐름은 막지 않는다.
export function markCheckoutSteps(steps) {
  fetch('/ai_modules/llm/checkout-step', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: getSessionId(), steps }),
    keepalive: true,
  }).catch(() => {})
}
