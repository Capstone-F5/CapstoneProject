import { SET_SIDES, SET_DRINKS, SET_SURCHARGE } from '../data/menuData'

// ─────────────────────────────────────────────────────────────────
// GET /api/menu?locale=ko → { categories: [CategoryOut], menu_items: { burger|side|beverage: [MenuItemOut] } }
// 이 함수가 백엔드 응답을 화면이 기대하는 { categories, menuItems, setSides, setDrinks, setSurcharge } 로 변환한다.
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL

// 백엔드 카테고리 키(name_en.lower()) → 프론트 카테고리 id
const CAT_KEY_MAP = { burger: 'burger', side: 'side', beverage: 'drink' }
const CAT_NAME_KO = { recommended: '추천메뉴', burger: '버거', side: '사이드', drink: '음료수' }
const CAT_EMOJI   = { recommended: '🍱', burger: '🍔', side: '🍟', drink: '🥤' }

function parseKcal(desc) {
  const m = desc.match(/(\d+)\s*kcal/)
  return m ? Number(m[1]) : null
}

// description 안의 "[F 버거] " 같은 이름 프리픽스 제거
function stripNamePrefix(desc) {
  return desc.replace(/^\[.*?\]\s*/, '')
}

function adaptItem(i, locale) {
  // 백엔드엔 한국어/영어 표기만 있음(중국어·일본어 번역 데이터 없음) — 한국어가 아니면
  // 전부 영어로 표기한다("외국어면 영어 메뉴로 표기").
  const isKo = locale === 'ko'
  const name = isKo ? i.name_ko : i.name_en
  // '없음'은 "제외 옵션 없음"을 나타내는 내부 값으로 앱 전역에서 그대로 비교되므로
  // (App.jsx/ItemDetailModal.jsx/CartScreen.jsx 등) 언어와 무관하게 항상 이 문자열을 쓴다.
  // 화면에 보여줄 때만 각 화면에서 로캘에 맞게 표시 문구로 바꾼다.
  const exclusions = [
    '없음',
    ...i.options.filter(o => o.option_group === 'EXCLUDE').map(o => (isKo ? o.name_ko : o.name_en)),
  ]
  const hasSet = i.options.some(o => o.option_group === 'SET_UPGRADE')
  return {
    id: i.id,
    name,
    price: Number(i.base_price),
    kcal: parseKcal(i.description),
    desc: stripNamePrefix(i.description),
    hasSet,
    exclusions,
    // 이미지는 DB(menu_items.image_url/set_image_url) 매칭을 그대로 사용 — 관리자 대시보드에서
    // 나중에 이 필드를 직접 관리할 수 있도록 프론트에 하드코딩된 이름 매핑을 두지 않는다.
    image: i.image_url ?? null,
    setImage: i.set_image_url ?? i.image_url ?? null,
    isPopular: i.is_popular,
    // 원본 options 보존 — App.jsx가 담기/카트 복원 시 selected_options 조립에 재사용
    options: i.options,
  }
}

export async function fetchMenuData(locale = 'ko') {
  const res = await fetch(`${API_BASE}/api/menu?locale=${encodeURIComponent(locale)}`)
  if (!res.ok) throw new Error(`menu fetch failed (${res.status})`)
  const raw = await res.json()

  const menuItems = {}
  for (const [backendKey, items] of Object.entries(raw.menu_items)) {
    const catId = CAT_KEY_MAP[backendKey] ?? backendKey
    menuItems[catId] = items.map(i => adaptItem(i, locale))
  }
  menuItems.recommended = Object.values(menuItems).flat().filter(i => i.isPopular)

  const categories = ['recommended', 'burger', 'side', 'drink']
    .filter(id => id === 'recommended' || menuItems[id])
    .map(id => ({ id, name: CAT_NAME_KO[id], emoji: CAT_EMOJI[id] }))

  return {
    categories,
    menuItems,
    // 세트 사이드/음료 선택 UI는 이름·이미지 표시용으로 menuData.js 상수를 계속 사용한다.
    // (실제 가격·주문 반영은 백엔드의 SET_SIDE/SET_DRINK 옵션이 담당 — 이름 문자열이
    //  backend/core/seed.py 의 시드값과 반드시 동일해야 한다)
    setSides: SET_SIDES,
    setDrinks: SET_DRINKS,
    setSurcharge: SET_SURCHARGE,
  }
}
