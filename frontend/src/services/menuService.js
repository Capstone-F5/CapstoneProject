import { menuItems, categories, SET_SIDES, SET_DRINKS, SET_SURCHARGE } from '../data/menuData'

// ─────────────────────────────────────────────────────────────────
// API 응답 스펙 (백엔드 연동 시 이 형식으로 맞춰주세요)
//
// GET /api/menu?locale=ko
// {
//   categories: [{ id: string, name: string, emoji?: string }],
//   menuItems: {
//     [categoryId]: [{
//       id: number,
//       name: string,          // 요청한 locale 언어로 반환
//       desc: string,          // 요청한 locale 언어로 반환
//       price: number,
//       kcal: number | null,
//       hasSet: boolean,
//       exclusions: string[],  // 요청한 locale 언어로 반환
//       image: string,         // e.g. "/images/burgers/F버거.png"
//       setImage: string       // e.g. "/images/sets/F버거 세트.png"
//     }]
//   },
//   setSides:    [{ name: string, extra: number, image: string }],
//   setDrinks:   [{ name: string, extra: number, image: string }],
//   setSurcharge: number
// }
//
// 지원 locale: ko | en | zh | ja
// ─────────────────────────────────────────────────────────────────

// VITE_API_URL을 .env 파일에 설정하면 자동으로 API 모드로 전환됩니다.
// 예) VITE_API_URL=http://localhost:8000
const API_BASE = import.meta.env.VITE_API_URL

export async function fetchMenuData(locale = 'ko') {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/menu?locale=${encodeURIComponent(locale)}`)
    if (!res.ok) throw new Error(`menu fetch failed (${res.status})`)
    return res.json()
  }

  // API 미연동 시 로컬 정적 데이터 사용
  // DB 연동 후에는 이 분기가 사라지고 위의 API 호출만 남습니다
  return {
    categories,
    menuItems,
    setSides: SET_SIDES,
    setDrinks: SET_DRINKS,
    setSurcharge: SET_SURCHARGE,
  }
}
