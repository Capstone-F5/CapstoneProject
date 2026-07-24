import { SET_SIDES, SET_DRINKS, SET_SURCHARGE } from '../data/menuData'
import { lookupImage, lookupSetImage } from '../data/imageMap'

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
  const name = locale === 'en' ? i.name_en : i.name_ko
  const exclusions = ['없음', ...i.options.filter(o => o.option_group === 'EXCLUDE').map(o => o.name_ko)]
  const hasSet = i.options.some(o => o.option_group === 'SET_UPGRADE')
  return {
    id: i.id,
    name,
    price: Number(i.base_price),
    kcal: parseKcal(i.description),
    desc: stripNamePrefix(i.description),
    hasSet,
    exclusions,
    image: lookupImage(i.name_ko),
    setImage: lookupSetImage(i.name_ko) ?? lookupImage(i.name_ko),
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
