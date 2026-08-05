import { SET_SIDES, SET_DRINKS, SET_SURCHARGE } from '../data/menuData'

// ─────────────────────────────────────────────────────────────────
// GET /api/menu?locale=ko → { categories: [CategoryOut], menu_items: { burger|side|beverage: [MenuItemOut] } }
// 이 함수가 백엔드 응답을 화면이 기대하는 { categories, menuItems, setSides, setDrinks, setSurcharge } 로 변환한다.
// ─────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// 백엔드 카테고리 키(name_en.lower()) → 프론트 카테고리 id.
// 여기 없는 카테고리는 name_en.lower() 값을 그대로 id로 쓴다 — 관리자가 새 카테고리를
// 추가해도(예: "디저트") 코드 수정 없이 그대로 새 탭으로 나타난다.
const CAT_KEY_MAP = { burger: 'burger', side: 'side', beverage: 'drink' }
// "추천메뉴"는 DB에 없는 가상 탭(is_popular 필터)이라 다국어 라벨을 여기서 직접 관리한다.
const RECOMMENDED_NAME = { ko: '추천메뉴', en: 'Recommended', zh: '推荐菜单', ja: 'おすすめ' }
const CAT_EMOJI = { recommended: '🍱', burger: '🍔', side: '🍟', drink: '🥤' }
const DEFAULT_CAT_EMOJI = '🍽️'

function parseKcal(desc) {
  const m = (desc ?? '').match(/(\d+)\s*kcal/)
  return m ? Number(m[1]) : null
}

function parseKcalStr(desc) {
  const m = (desc ?? '').match(/(\d+)\s*kcal/)
  return m ? `${m[1]} kcal` : ''
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
  // 외국어 locale에서는 한국어 설명 텍스트 대신 kcal 수치만 표시
  const desc = isKo ? stripNamePrefix(i.description) : parseKcalStr(i.description)
  return {
    id: i.id,
    categoryId: i.category_id,
    name,
    price: Number(i.base_price),
    kcal: parseKcal(i.description),
    desc,
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

export async function fetchActiveDiscounts() {
  try {
    const res = await fetch(`${API_BASE}/api/orders/active-discounts`)
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

export async function fetchMenuData(locale = 'ko') {
  const [menuRes, activeDiscounts] = await Promise.all([
    fetch(`${API_BASE}/api/menu?locale=${encodeURIComponent(locale)}`),
    fetchActiveDiscounts(),
  ])
  const res = menuRes
  if (!res.ok) throw new Error(`menu fetch failed (${res.status})`)
  const raw = await res.json()

  const menuItems = {}
  for (const [backendKey, items] of Object.entries(raw.menu_items)) {
    const catId = CAT_KEY_MAP[backendKey] ?? backendKey
    menuItems[catId] = items.map(i => adaptItem(i, locale))
  }
  menuItems.recommended = Object.values(menuItems).flat().filter(i => i.isPopular)

  // DB의 실제 카테고리 목록을 그대로 반영 — 관리자가 카테고리를 추가/이름변경/순서변경/숨김
  // 처리하면(is_visible) 코드 수정 없이 그대로 반영된다. "추천메뉴"만 DB에 없는 가상 탭이라
  // 맨 앞에 직접 붙인다. 백엔드가 이미 display_order 순 + is_visible 필터링해서 내려준다.
  const dbCategories = (raw.categories || []).map(c => {
    const id = CAT_KEY_MAP[c.name_en.toLowerCase()] ?? c.name_en.toLowerCase()
    return {
      id,
      name: locale === 'ko' ? c.name_ko : c.name_en,
      image: c.image_url ?? null,
      emoji: CAT_EMOJI[id] ?? DEFAULT_CAT_EMOJI,
    }
  })

  const categories = [
    { id: 'recommended', name: RECOMMENDED_NAME[locale] ?? RECOMMENDED_NAME.en, image: null, emoji: CAT_EMOJI.recommended },
    ...dbCategories,
  ]

  return {
    categories,
    menuItems,
    activeDiscounts,
    // 세트 사이드/음료 선택 UI는 이름·이미지 표시용으로 menuData.js 상수를 계속 사용한다.
    // (실제 가격·주문 반영은 백엔드의 SET_SIDE/SET_DRINK 옵션이 담당 — 이름 문자열이
    //  backend/core/seed.py 의 시드값과 반드시 동일해야 한다)
    setSides: SET_SIDES,
    setDrinks: SET_DRINKS,
    setSurcharge: SET_SURCHARGE,
  }
}
