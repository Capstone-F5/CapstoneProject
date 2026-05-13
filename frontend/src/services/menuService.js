import { menuItems, categories, SET_SIDES, SET_DRINKS, SET_SURCHARGE } from '../data/menuData'

// ─────────────────────────────────────────────────────────────────
// API 응답 스펙 (백엔드 연동 시 이 형식으로 맞춰주세요)
//
// GET /api/menu
// {
//   categories: [{ id: string, name: string }],
//   menuItems: {
//     [categoryId]: [{
//       id: number, name: string, price: number, kcal: number|null,
//       desc: string, hasSet: boolean, exclusions: string[],
//       image: string,       // e.g. "/images/burgers/F버거.png"
//       setImage: string     // e.g. "/images/sets/F버거 세트.png"
//     }]
//   },
//   setSides:    [{ name: string, extra: number, image: string }],
//   setDrinks:   [{ name: string, extra: number, image: string }],
//   setSurcharge: number
// }
// ─────────────────────────────────────────────────────────────────

// VITE_API_URL을 .env 파일에 설정하면 자동으로 API 모드로 전환됩니다.
// 예) VITE_API_URL=http://localhost:8000
const API_BASE = import.meta.env.VITE_API_URL

export async function fetchMenuData() {
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/api/menu`)
    if (!res.ok) throw new Error(`메뉴 로드 실패 (${res.status})`)
    return res.json()
  }

  // API 미연동 시 정적 데이터 사용
  return { menuItems, categories, SET_SIDES, SET_DRINKS, SET_SURCHARGE }
}
