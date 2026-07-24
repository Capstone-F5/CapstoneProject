// 장바구니 서비스 — 백엔드 카트(session_id 기준)를 단일 소스로 사용한다.
// 터치 UI와 음성 주문(LLM)이 동일한 백엔드 카트를 실시간으로 공유한다.
import { getSessionId } from './session'

const API_BASE = import.meta.env.VITE_API_URL

async function req(path, opts) {
  const res = await fetch(`${API_BASE}${path}`, opts)
  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { /* ignore */ }
    throw new Error(detail || `요청 실패 (${res.status})`)
  }
  return res.status === 204 ? null : res.json()
}

export const fetchCart = () => req(`/api/cart/${getSessionId()}`)

export const addCartItem = ({ menu_item_id, quantity = 1, selected_options = [], special_note = null }) =>
  req(`/api/cart/${getSessionId()}/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ menu_item_id, quantity, selected_options, special_note }),
  })

export const updateCartItem = (cartItemId, patch) =>
  req(`/api/cart/${getSessionId()}/items/${cartItemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })

export const removeCartItem = (cartItemId) =>
  req(`/api/cart/${getSessionId()}/items/${cartItemId}`, { method: 'DELETE' })

export const clearCartApi = () =>
  req(`/api/cart/${getSessionId()}`, { method: 'DELETE' })
