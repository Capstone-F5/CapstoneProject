// 카트(session-scoped) API와 LLM 대화가 동일한 세션을 가리키도록 세션 ID를 한 곳에서 관리한다.
const SESSION_KEY = 'kiosk_llm_session_id'

export function getSessionId() {
  let sid = sessionStorage.getItem(SESSION_KEY)
  if (!sid) sid = newSessionId()
  return sid
}

export function newSessionId() {
  const sid = crypto.randomUUID?.() ?? `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`
  sessionStorage.setItem(SESSION_KEY, sid)
  return sid
}
