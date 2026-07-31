// 대기화면 배경 슬라이드 목록 — 관리자가 DB에서 교체/추가/비활성화할 수 있다.
const API_BASE = import.meta.env.VITE_API_URL ?? ''

const FALLBACK_IMAGES = ['/bg.png']

export async function fetchStartScreenImages() {
  try {
    const res = await fetch(`${API_BASE}/api/settings/start-screen-images`)
    if (!res.ok) throw new Error(`start screen images fetch failed (${res.status})`)
    const data = await res.json()
    const urls = data.map(i => i.image_url).filter(Boolean)
    return urls.length ? urls : FALLBACK_IMAGES
  } catch (e) {
    console.error('[settingsService] 대기화면 이미지 조회 실패, 기본값 사용:', e)
    return FALLBACK_IMAGES
  }
}
