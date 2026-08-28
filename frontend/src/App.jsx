import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { useGesture } from './hooks/useGesture'
import { LocaleProvider, useLocale } from './i18n/LocaleContext'
import * as cartService from './services/cartService'
import CollectTool from './tools/CollectTool'
import StartScreen from './screens/StartScreen'
import OrderTypeScreen from './screens/OrderTypeScreen'
import MenuScreen from './screens/MenuScreen'
import CartScreen from './screens/CartScreen'
import PaymentScreen from './screens/PaymentScreen'
import CompletionScreen from './screens/CompletionScreen'
import CardPaymentScreen from './screens/CardPaymentScreen'
import PayPaymentScreen from './screens/PayPaymentScreen'
import CashPaymentScreen from './screens/CashPaymentScreen'
import ChatPanel from './components/ChatPanel'
import { useMenuData } from './hooks/useMenuData'

// 자석 클릭 도우미 함수 추가
// 포인터 주변 반경(radius) 내에 있는 버튼 찾음
function getClickableElement(x, y, radius = 30) {
  // 1순위: 정확히 포인터 위치에 요소가 있는지 확인
  let el = document.elementFromPoint(x, y)
  if (el && (el.tagName === 'BUTTON' || el.closest('button'))) {
    return el.closest('button') || el
  }

  // 빗나갔다면 주변 반경(30px)을 8방향으로 탐색해서 자석처럼 버튼을 찾음
  const offsets = [
    [0, -radius], [0, radius], [-radius, 0], [radius, 0],
    [-radius, -radius], [radius, -radius], [-radius, radius], [radius, radius]
  ]

  for (const [dx, dy] of offsets) {
    const neighbor = document.elementFromPoint(x + dx, y + dy)
    if (neighbor) {
      const btn = neighbor.closest('button')
      if (btn) return btn // 주변에서 버튼을 찾으면 즉시 반환!
    }
  }

  return el // 끝끝내 못 찾으면 원래 위치의 요소 반환
}

// 제스처 키 → 표시 문자열 (컴포넌트 외부 상수)
const GESTURE_LABELS = {
  swipe_right: '→ 다음',
  swipe_left:  '← 이전',
  swipe_up:    '↑ 위로',
  swipe_down:  '↓ 아래로',
  ok:          '✓ 확인',
  finger_1:    '☝ 1',
  finger_2:    '✌ 2',
  finger_3:    '3',
  finger_4:    '4',
  finger_5:    '✋ 5',
}

const _isCollect = new URLSearchParams(window.location.search).has('collect')

// orderType 화면 진입 직후, 직전 화면의 OK 핀치 해제 과도기 동작을 매장/포장 선택으로
// 오인식하지 않도록 무시하는 유예 구간(ms)
const ORDER_TYPE_GESTURE_GRACE_MS = 900

// 접근성 컨트롤 바(음성인식/제스처/카메라) 고정 높이
const CONTROL_BAR_HEIGHT = 58

// 메뉴 원본(options 포함)에서 특정 그룹의 옵션을 이름으로 찾는다.
// name이 없으면(SET_UPGRADE처럼 단일 옵션인 경우) 그룹만으로 찾는다.
function findOption(menu, group, name) {
  return menu?.options?.find(o => o.option_group === group && (name == null || o.name_ko === name))
}

// 백엔드 CartItemOut → 화면(CartItem 등)이 기대하는 로컬 카트 항목 형태로 역매핑.
function adaptCartItem(ci, menuById) {
  const menu = menuById[ci.menu_item_id]
  const opts = ci.selected_options || []
  const matchGroup = (group) => {
    for (const sel of opts) {
      const opt = menu?.options?.find(o => o.id === sel.option_id)
      if (opt && opt.option_group === group) return opt
    }
    return null
  }
  const isSet    = !!matchGroup('SET_UPGRADE')
  const exclOpt  = matchGroup('EXCLUDE')
  const sideOpt  = matchGroup('SET_SIDE')
  const drinkOpt = matchGroup('SET_DRINK')
  return {
    cartId: ci.cart_item_id,
    id: ci.menu_item_id,
    categoryId: menu?.categoryId ?? null,
    name: menu?.name ?? ci.name_ko,
    image: isSet ? (menu?.setImage ?? menu?.image) : menu?.image,
    type: isSet ? 'set' : 'single',
    qty: ci.quantity,
    unitPrice: Number(ci.unit_price),
    exclusion: exclOpt?.name_ko ?? '없음',
    side: sideOpt?.name_ko ?? null,
    sideExtra: Number(sideOpt?.additional_price ?? 0),
    drink: drinkOpt?.name_ko ?? null,
    drinkExtra: Number(drinkOpt?.additional_price ?? 0),
    special_note: ci.special_note,
    key: ci.cart_item_id,
  }
}

// LocaleProvider 바깥에서는 useLocale() 호출 불가 → AppContent로 분리
function AppContent() {
  const { setLocale } = useLocale()
  // UI에서 쓰는 메뉴 데이터와 동일한 소스 — API 연동 시에도 자동 반영
  const { menuData } = useMenuData()
  const [screen,    setScreen]    = useState('start')
  const [cart,      setCart]      = useState([])
  const [orderType, setOrderType] = useState(null)
  const [orderNum,  setOrderNum]  = useState(null)
  const [chatOpen,  setChatOpen]  = useState(false)
  const [voiceToast, setVoiceToast] = useState(null)   // AI 동작 알림
  const voiceToastTimer = useRef(null)

  // 손동작 인식 On/Off & PiP 표시 (localStorage 영구 저장)
  const [gestureEnabled, setGestureEnabled] = useState(() => {
    const v = localStorage.getItem('gestureEnabled')
    return v === null ? true : v === 'true'
  })
  const [pipEnabled, setPipEnabled] = useState(() => {
    return localStorage.getItem('pipEnabled') === 'true'
  })
  useEffect(() => { localStorage.setItem('gestureEnabled', String(gestureEnabled)) }, [gestureEnabled])
  useEffect(() => { localStorage.setItem('pipEnabled',     String(pipEnabled))     }, [pipEnabled])

  // PiP 캔버스 — useGesture가 매 프레임 카메라 영상 + 관절을 직접 그림
  const pipCanvasRef = useRef(null)

  // 포인터 — DOM 직접 조작으로 React 리렌더 없이 30fps 업데이트
  const pointerRef    = useRef(null)   // 최신 위치 { x, y }
  const pointerDivRef = useRef(null)   // 커서 DOM 노드

  // OK 로딩 링 — DOM 직접 조작
  const okRingRef = useRef(null)
  const okRafRef  = useRef(null)

  // 엣지 존 — DOM 직접 조작
  const EDGE_MARGIN    = 0.10   // 화면 크기의 10%
  const EDGE_MAX_SPEED = 500    // px/s (최대 강도일 때)
  const edgeTopRef    = useRef(null)
  const edgeBottomRef = useRef(null)
  const edgeLeftRef   = useRef(null)
  const edgeRightRef  = useRef(null)
  const edgeStateRef  = useRef({ left: 0, right: 0, top: 0, bottom: 0 })
  const edgeRafRef    = useRef(null)
  const edgeLastTRef  = useRef(null)

  const menuSwipeRef   = useRef(null)
  const menuModalRef   = useRef(null)
  const menuScrollRef  = useRef(null)  // 메뉴 가로 스크롤(쥐고 끌기) 연결용
  const fingerCountRef = useRef(null)  // 수량 조절 팝업(손가락 개수) 연결용

  // 음성 화면 제어: 현재 화면이 등록하는 액션 핸들러 + 대기 액션 큐
  const screenVoiceRef    = useRef(null)
  const pendingActionsRef = useRef([])
  const awaitingScreenRef = useRef(false)   // navigate 후 새 화면 마운트 대기 중 여부
  const drainTimerRef     = useRef(null)     // 화면 마운트 지연 시 재드레인 폴백 타이머
  // 현재 열린 메뉴 팝업 상태 — LLM이 선택 내용을 읽고 수정하는 데 사용
  const modalStateRef     = useRef(null)

  // 음성 액션 핸들러가 항상 최신 데이터를 읽도록 ref로 유지
  const appCartRef    = useRef(cart)
  const menuDataRef   = useRef(menuData)
  const menuByIdRef   = useRef({})
  appCartRef.current  = cart
  menuDataRef.current = menuData

  // 현재 화면을 ref로 유지 — handleGesture 콜백 재생성 없이 참조
  const screenRef = useRef(screen)
  const screenEnteredAtRef = useRef(performance.now())
  useEffect(() => {
    screenRef.current = screen
    screenEnteredAtRef.current = performance.now()
  }, [screen])

  // 화면별 제스처 액션 — 렌더마다 최신 클로저를 갱신
  const gestureActionsRef = useRef({})
  gestureActionsRef.current = {
    orderType: {
      dineIn:  () => { setOrderType('dine-in'); setScreen('menu') },
      takeout: () => { setOrderType('takeout');  setScreen('menu') },
    },
  }

  // 감지된 제스처 표시용 (일시적 알림)
  const [gestureLabel, setGestureLabel] = useState(null)
  const labelTimerRef = useRef(null)

  const showLabel = useCallback((text) => {
    setGestureLabel(text)
    clearTimeout(labelTimerRef.current)
    labelTimerRef.current = setTimeout(() => setGestureLabel(null), 1200)
  }, [])

  // ── 포인터 민감도 ────────────────────────────────────────────────────────
  const POINTER_SENS_X = 1.0
  const POINTER_SENS_Y = 1.0

  // 정규화 좌표(MediaPipe 0~1, 좌우 반전 전) → 화면 픽셀로 변환
  const normToScreen = useCallback(({ x, y }) => {
    const nx = (1 - x) - 0.5   // 좌우 반전 후 중심 기준
    const ny = y - 0.5
    return {
      x: (0.5 + nx * POINTER_SENS_X) * window.innerWidth,
      y: (0.5 + ny * POINTER_SENS_Y) * window.innerHeight,
    }
  }, [])

  // 제스처 활동 → idle 타이머 리셋용 커스텀 이벤트 (2초 스로틀)
  const lastActivityRef = useRef(0)
  const dispatchActivity = useCallback(() => {
    const now = Date.now()
    if (now - lastActivityRef.current > 2000) {
      lastActivityRef.current = now
      window.dispatchEvent(new Event('gesture-activity'))
    }
  }, [])

  // 엣지 인디케이터 opacity 초기화
  const clearEdge = useCallback(() => {
    edgeStateRef.current = { left: 0, right: 0, top: 0, bottom: 0 }
    if (edgeTopRef.current)    edgeTopRef.current.style.opacity    = 0
    if (edgeBottomRef.current) edgeBottomRef.current.style.opacity = 0
    if (edgeLeftRef.current)   edgeLeftRef.current.style.opacity   = 0
    if (edgeRightRef.current)  edgeRightRef.current.style.opacity  = 0
  }, [])

  // 포인터: useGesture 의 onPointer 콜백 — React state 없이 DOM 직접 업데이트
  const handlePointer = useCallback((norm) => {
    if (!norm) {
      pointerRef.current = null
      if (pointerDivRef.current) pointerDivRef.current.style.opacity = '0'
      clearEdge()
      return
    }
    const p = normToScreen(norm)
    pointerRef.current = p
    const d = pointerDivRef.current
    if (d) {
      d.style.left    = `${p.x - 14}px`
      d.style.top     = `${p.y - 14}px`
      d.style.opacity = '1'
    }

    // ── 엣지 존 감지 ──────────────────────────────────────────────────────
    const nx = p.x / window.innerWidth
    const ny = p.y / window.innerHeight
    const eL = Math.max(0, (EDGE_MARGIN - nx)       / EDGE_MARGIN)
    const eR = Math.max(0, (EDGE_MARGIN - (1 - nx)) / EDGE_MARGIN)
    const eT = Math.max(0, (EDGE_MARGIN - ny)       / EDGE_MARGIN)
    const eB = Math.max(0, (EDGE_MARGIN - (1 - ny)) / EDGE_MARGIN)

    if (edgeTopRef.current)    edgeTopRef.current.style.opacity    = eT
    if (edgeBottomRef.current) edgeBottomRef.current.style.opacity = eB
    if (edgeLeftRef.current)   edgeLeftRef.current.style.opacity   = eL
    if (edgeRightRef.current)  edgeRightRef.current.style.opacity  = eR

    edgeStateRef.current = { left: eL, right: eR, top: eT, bottom: eB }

    if ((eL + eR + eT + eB) > 0 && !edgeRafRef.current) {
      edgeLastTRef.current = null
      const tick = (t) => {
        const cur = pointerRef.current
        if (!cur) { edgeRafRef.current = null; return }
        const e = edgeStateRef.current
        if (e.left + e.right + e.top + e.bottom === 0) { edgeRafRef.current = null; return }

        const dt = edgeLastTRef.current !== null ? (t - edgeLastTRef.current) / 1000 : 0
        edgeLastTRef.current = t

        if (dt > 0) {
          const dx = (e.right - e.left) * EDGE_MAX_SPEED * dt
          const dy = (e.bottom - e.top) * EDGE_MAX_SPEED * dt
          let el = document.elementFromPoint(cur.x, cur.y)
          let scrolled = false
          while (el && el !== document.documentElement) {
            const cs   = window.getComputedStyle(el)
            const canY = (cs.overflowY === 'auto' || cs.overflowY === 'scroll') && el.scrollHeight > el.clientHeight
            const canX = (cs.overflowX === 'auto' || cs.overflowX === 'scroll') && el.scrollWidth  > el.clientWidth
            if (canY || canX) {
              if (canY) el.scrollTop  += dy
              if (canX) el.scrollLeft += dx
              scrolled = true
              break
            }
            el = el.parentElement
          }
          if (!scrolled) window.scrollBy(0, dy)
        }
        edgeRafRef.current = requestAnimationFrame(tick)
      }
      edgeRafRef.current = requestAnimationFrame(tick)
    }

    dispatchActivity()
  }, [normToScreen, dispatchActivity, clearEdge])

  const OK_MOVE_THRESHOLD = 80

  const fireOk = useCallback(() => {
    if (okRafRef.current !== null) return
    const p = pointerRef.current
    if (!p) return

    const startX   = p.x
    const startY   = p.y
    const start    = performance.now()
    const DURATION = 500
    const ring     = okRingRef.current

    if (ring) {
      ring.style.display    = 'block'
      ring.style.left       = `${startX - 28}px`
      ring.style.top        = `${startY - 28}px`
      ring.style.background = `conic-gradient(rgba(80,210,255,0.95) 0deg, rgba(255,255,255,0.18) 0deg)`
    }

    const tick = (now) => {
      const cur = pointerRef.current
      if (!cur || Math.hypot(cur.x - startX, cur.y - startY) > OK_MOVE_THRESHOLD) {
        okRafRef.current = null
        if (ring) ring.style.display = 'none'
        return
      }

      const progress = Math.min((now - start) / DURATION, 1)
      if (ring) ring.style.background =
        `conic-gradient(rgba(80,210,255,0.95) ${progress * 360}deg, rgba(255,255,255,0.18) 0deg)`

      if (progress < 1) {
        okRafRef.current = requestAnimationFrame(tick)
      } else {
        okRafRef.current = null
        if (ring) ring.style.display = 'none'
        
        // 자석 클릭 적용
        const el = getClickableElement(startX, startY, 30)
        if (el) el.click()
      }
    }
    okRafRef.current = requestAnimationFrame(tick)
  }, [])

  const scrollAtPointer = useCallback((dy) => {
    const p = pointerRef.current
    let el = p ? document.elementFromPoint(p.x, p.y) : null
    while (el && el !== document.documentElement) {
      const { overflowY } = window.getComputedStyle(el)
      if ((overflowY === 'auto' || overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
        el.scrollBy({ top: dy, behavior: 'smooth' })
        return
      }
      el = el.parentElement
    }
    window.scrollBy({ top: dy, behavior: 'smooth' })
  }, [])

  const [gestureHud, setGestureHud] = useState(null)

  const handleGesture = useCallback(({ gesture, hands, total_fingers }) => {
    // HUD 업데이트
    setGestureHud({
      left:  hands?.left  ? `${hands.left.finger_count}개`  : '-',
      right: hands?.right ? `${hands.right.finger_count}개` : '-',
      total: total_fingers ?? 0,
    })

    const currentScreen = screenRef.current
    const activeHand = hands?.right || hands?.left
    
    if (activeHand) {
      if (menuScrollRef.current && (activeHand.is_pinching || activeHand.scroll_dx !== 0)) {
        menuScrollRef.current(activeHand.scroll_dx, activeHand.is_pinching)
      }
      if (fingerCountRef.current && activeHand.stable_fingers !== null) {
        fingerCountRef.current(activeHand.stable_fingers)
      }
    }

    if (!gesture) return

    // ── 랜딩 페이지: 커서 + OK만 ─────────────────────
    if (currentScreen === 'start') {
      if (gesture === 'ok') { fireOk(); showLabel(GESTURE_LABELS.ok) }
      return
    }

    // ── 식사 장소 선택: OK(포인터 클릭) + 1(매장) + 2(포장) ──
    if (currentScreen === 'orderType') {
      const { dineIn, takeout } = gestureActionsRef.current.orderType
      const fingerCount = activeHand?.finger_count ?? -1
      const settled = performance.now() - screenEnteredAtRef.current >= ORDER_TYPE_GESTURE_GRACE_MS
      if      (gesture === 'ok')                                        { fireOk(); showLabel(GESTURE_LABELS.ok) }
      else if (settled && gesture === 'finger_1' && fingerCount <= 1)  { dineIn();  showLabel('☝ 매장') }
      else if (settled && gesture === 'finger_2' && fingerCount >= 2)  { takeout(); showLabel('✌ 포장') }
      return
    }

    // ── 나머지 모든 페이지 ────────────────────────────
    if (gesture === 'ok') {
      fireOk()
      showLabel(GESTURE_LABELS.ok)
      return
    }

    if (gesture === 'swipe_up') {
      scrollAtPointer(-260)
      showLabel(GESTURE_LABELS.swipe_up)
      return
    }

    if (gesture === 'swipe_down') {
      scrollAtPointer(260)
      showLabel(GESTURE_LABELS.swipe_down)
      return
    }

    // 메뉴 화면 모달 제스처 (단품/세트 선택)
    if (currentScreen === 'menu' && menuModalRef.current) {
      if (gesture === 'finger_1') { menuModalRef.current('single'); showLabel('☝ 단품'); return }
      if (gesture === 'finger_2') { menuModalRef.current('set');    showLabel('✌ 세트');  return }
    }

    // 메뉴 화면 좌우 스와이프 → 페이지/탭 전환
    if (currentScreen === 'menu' && (gesture === 'swipe_left' || gesture === 'swipe_right')) {
      menuSwipeRef.current?.(gesture === 'swipe_right' ? 'left' : 'right')
      showLabel(GESTURE_LABELS[gesture])
      return
    }

    if (gesture.startsWith('swipe_')) showLabel(GESTURE_LABELS[gesture])
  }, [showLabel, fireOk, scrollAtPointer])

  useGesture({
    onPointer:    handlePointer,
    onGesture:    handleGesture,
    enabled:      gestureEnabled,
    pipCanvasRef: gestureEnabled && pipEnabled ? pipCanvasRef : null,
  })

  useEffect(() => {
    if (gestureEnabled) return
    pointerRef.current = null
    if (pointerDivRef.current) pointerDivRef.current.style.opacity = '0'
    if (okRingRef.current)     okRingRef.current.style.display     = 'none'
    if (okRafRef.current) { cancelAnimationFrame(okRafRef.current); okRafRef.current = null }
    if (edgeRafRef.current) { cancelAnimationFrame(edgeRafRef.current); edgeRafRef.current = null }
    edgeStateRef.current = { left: 0, right: 0, top: 0, bottom: 0 }
  }, [gestureEnabled])


  const nav = (s) => {
    if (s === 'start') {
      setChatOpen(false)
      setLocale('ko')
      sessionStorage.removeItem('kiosk_detected_lang')
      window.dispatchEvent(new CustomEvent('kiosk-session-reset'))
    }
    setScreen(s)
  }

  const refreshCart = useCallback(async () => {
    try {
      const data = await cartService.fetchCart()
      setCart(data.items.map(ci => adaptCartItem(ci, menuByIdRef.current)))
    } catch (e) {
      console.error('[cart] refresh 실패:', e)
      showVoiceToast('오류: 장바구니를 불러오지 못했습니다')
    }
  }, [])

  const addToCart = async (draft) => {
    const menu = menuByIdRef.current[draft.id]
    if (!menu) { console.warn('[cart] 알 수 없는 메뉴:', draft.id); return }

    const selected_options = []
    if (draft.type === 'set') {
      const su = findOption(menu, 'SET_UPGRADE')
      if (su) selected_options.push({ option_id: su.id, name: su.name_ko })
      if (draft.side)  { const s = findOption(menu, 'SET_SIDE',  draft.side);  if (s) selected_options.push({ option_id: s.id, name: s.name_ko }) }
      if (draft.drink) { const d = findOption(menu, 'SET_DRINK', draft.drink); if (d) selected_options.push({ option_id: d.id, name: d.name_ko }) }
    }
    if (draft.exclusion && draft.exclusion !== '없음') {
      const ex = findOption(menu, 'EXCLUDE', draft.exclusion)
      if (ex) selected_options.push({ option_id: ex.id, name: ex.name_ko })
    }

    try {
      await cartService.addCartItem({
        menu_item_id: draft.id,
        quantity: draft.qty ?? 1,
        selected_options,
        special_note: draft.special_note ?? null,
      })
      await refreshCart()
    } catch (e) {
      console.error('[cart] 담기 실패:', e)
      showVoiceToast(`오류: ${e.message || '장바구니 담기에 실패했습니다'}`)
    }
  }

  const updateQty = async (cartId, qty) => {
    setCart(prev => qty <= 0 ? prev.filter(c => c.cartId !== cartId)
                              : prev.map(c => c.cartId === cartId ? { ...c, qty } : c))
    try {
      if (qty <= 0) await cartService.removeCartItem(cartId)
      else          await cartService.updateCartItem(cartId, { quantity: qty })
    } catch (e) {
      console.error('[cart] 수량 변경 실패:', e)
      showVoiceToast(`오류: ${e.message || '수량 변경에 실패했습니다'}`)
      await refreshCart()
    }
  }

  const clearCart = async () => {
    setCart([])
    try {
      await cartService.clearCartApi()
    } catch (e) {
      console.error('[cart] 초기화 실패:', e)
    }
  }

  const cartForLLM = useMemo(() =>
    cart.map(c => ({
      cart_id:   c.cartId,
      menu_id:   c.id,
      name:      c.name,
      item_type: c.type,
      quantity:  c.qty,
      unit_price: c.unitPrice,
      exclusion: c.exclusion,
      side:      c.side,
      drink:     c.drink,
    }))
  , [cart])

  const _menuById = useMemo(() => {
    if (!menuData?.menuItems) return {}
    const map = {}
    Object.values(menuData.menuItems).forEach(list => list.forEach(m => { map[m.id] = m }))
    return map
  }, [menuData])
  menuByIdRef.current = _menuById

  const cartRestoredRef = useRef(false)
  useEffect(() => {
    if (menuData && !cartRestoredRef.current) {
      cartRestoredRef.current = true
      refreshCart()
    }
  }, [menuData, refreshCart])

  function execAppAction(a) {
    switch (a.type) {
      case 'add_item': {
        screenVoiceRef.current?.({...a, type: 'add_item'})
        refreshCart()
        return 'handled'
      }
      case 'update_qty':
        return 'handled'
      case 'remove_item':
      case 'update_item':
      case 'clear_cart':
        refreshCart()
        return 'handled'
      case 'navigate':
        nav(a.screen)
        return 'nav'
      case 'checkout':
        nav('cart')
        return 'nav'
      case 'order_type':
        setOrderType(a.value === 'takeout' ? 'takeout' : 'dine-in')
        nav('menu')
        return 'nav'
      case 'set_language':
        if (a.value) setLocale(a.value)
        return 'handled'
      case 'set_gesture':
        setGestureEnabled(a.value === 'on')
        return 'handled'
      case 'set_camera':
        setPipEnabled(a.value === 'on')
        return 'handled'
      default:
        return 'no'
    }
  }

  function drainVoiceActions() {
    const q = pendingActionsRef.current
    while (q.length) {
      const a = q[0]
      const res = execAppAction(a)
      if (res === 'nav') {
        q.shift()
        awaitingScreenRef.current = true
        break
      }
      if (res === 'handled') { q.shift(); continue }
      if (!screenVoiceRef.current) {
        scheduleDrainRetry()
        break
      }
      const handled = screenVoiceRef.current(a)
      if (handled) { q.shift(); continue }
      if (awaitingScreenRef.current) {
        scheduleDrainRetry()
        break
      }
      console.warn('[voice] 현재 화면에서 처리할 수 없는 액션, 무시:', a)
      q.shift()
    }
  }

  function scheduleDrainRetry(attempt = 0) {
    if (drainTimerRef.current) clearTimeout(drainTimerRef.current)
    if (attempt > 20) {
      awaitingScreenRef.current = false
      if (pendingActionsRef.current.length) {
        console.warn('[voice] 대기 액션 처리 실패, 폐기:', pendingActionsRef.current.splice(0))
      }
      return
    }
    drainTimerRef.current = setTimeout(() => {
      const before = pendingActionsRef.current.length
      drainVoiceActions()
      if (pendingActionsRef.current.length && pendingActionsRef.current.length === before
          && awaitingScreenRef.current) {
        scheduleDrainRetry(attempt + 1)
      }
    }, 50)
  }

  function actionToMsg(a) {
    const menuName = a.name || (appCartRef.current.find(c => c.id === a.menu_id)?.name) || `메뉴#${a.menu_id}`
    const catLabel = { recommended: '추천메뉴', burger: '버거', side: '사이드', drink: '음료수' }
    const screenLabel = { start: '시작', orderType: '주문유형', menu: '메뉴', cart: '장바구니', complete: '완료' }
    switch (a.type) {
      case 'add_item':        return `장바구니 추가: ${menuName} ${a.quantity || 1}개`
      case 'update_qty':      return `수량 변경: ${a.quantity}개`
      case 'remove_item':     return `삭제: ${menuName}`
      case 'update_item':     return `옵션 변경: ${menuName}`
      case 'clear_cart':      return '장바구니 전체 삭제'
      case 'navigate':        return `화면 이동: ${screenLabel[a.screen] || a.screen}`
      case 'checkout':        return '장바구니로 이동'
      case 'order_type':      return a.value === 'dine-in' ? '매장 식사 선택' : '포장 선택'
      case 'select_category': return `카테고리: ${catLabel[a.value] || a.value}`
      case 'menu_page':       return a.value === 'next' ? '다음 페이지' : '이전 페이지'
      case 'open_item':       return `메뉴 상세 열기`
      case 'update_modal':    return `팝업 수정: ${a.field} → ${a.value}`
      case 'start_checkout':  return '결제 시작'
      case 'points':          return a.value === 'yes' ? '포인트 적립' : '포인트 미적립'
      case 'points_phone':    return `전화번호: ${a.phone || ''}`
      case 'payment_method':  return `결제 수단: ${{ card:'카드', cash:'현금', pay:'간편결제' }[a.value] || a.value}`
      case 'set_language':    return `언어 변경: ${a.value}`
      case 'set_gesture':     return `손동작 ${a.value === 'on' ? 'ON' : 'OFF'}`
      case 'set_camera':      return `카메라 ${a.value === 'on' ? 'ON' : 'OFF'}`
      default:                return null
    }
  }

  function showVoiceToast(msg) {
    if (!msg) return
    clearTimeout(voiceToastTimer.current)
    setVoiceToast({ msg, key: Date.now() })
    voiceToastTimer.current = setTimeout(() => setVoiceToast(null), 2500)
  }

  function handleVoiceAction(a) {
    showVoiceToast(actionToMsg(a))
    pendingActionsRef.current.push(a)
    drainVoiceActions()
  }

  useEffect(() => {
    awaitingScreenRef.current = false
    if (pendingActionsRef.current.length) drainVoiceActions()
  }, [screen]) 

  const total = cart.reduce((sum, c) => sum + c.unitPrice * c.qty, 0)
  
  const props = { cart, total, addToCart, updateQty, clearCart, nav, setOrderNum, orderType, setOrderType, chatOpen, fingerCountRef }

  const screens = {
    start:       <StartScreen {...props} />,
    orderType:   <OrderTypeScreen nav={nav} setOrderType={setOrderType} />,
    menu:        <MenuScreen {...props} swipeRef={menuSwipeRef} modalRef={menuModalRef} voiceRef={screenVoiceRef} modalStateRef={modalStateRef} scrollRef={menuScrollRef} />,
    cart:        <CartScreen {...props} voiceRef={screenVoiceRef} />,
    payment:     <PaymentScreen {...props} />,
    complete:    <CompletionScreen orderNum={orderNum} nav={nav} />,
    cardPayment: <CardPaymentScreen {...props} />,
    payPayment:  <PayPaymentScreen {...props} />,
    cashPayment: <CashPaymentScreen {...props} />,
  }

  return (
    <>
        {/* ── AI 동작 토스트 알림 ── */}
        {voiceToast && (
          <div key={voiceToast.key} style={{
            position: 'fixed',
            bottom: chatOpen ? 'calc(33vh + 72px)' : 80,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(116,64,50,0.92)',
            color: '#fff',
            padding: '10px 22px',
            borderRadius: 24,
            fontSize: 15,
            fontWeight: 600,
            pointerEvents: 'none',
            zIndex: 9050,
            whiteSpace: 'nowrap',
            boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
          }}>
            AI: {voiceToast.msg}
          </div>
        )}

        {/* ── 테스트 HUD (좌측 하단) ── */}
        {gestureHud && (
          <div style={{
            position: 'fixed', bottom: 16, left: 16,
            background: 'rgba(0,0,0,0.75)', color: '#fff',
            padding: '10px 16px', borderRadius: 10,
            fontSize: 13, lineHeight: 1.8,
            fontFamily: 'monospace', pointerEvents: 'none', zIndex: 9002,
          }}>
            <div>왼손 &nbsp;: {gestureHud.left}</div>
            <div>오른손: {gestureHud.right}</div>
            <div>합계 &nbsp;: {gestureHud.total}개</div>
            <div style={{ color: gestureLabel ? '#7fff7f' : '#888' }}>
              제스처: {gestureLabel ?? '-'}
            </div>
          </div>
        )}

        {/* ── 제스처 포인터 — DOM 직접 조작, React 리렌더 없음 ── */}
        <div ref={pointerDivRef} style={{
          position: 'fixed',
          left: -100, top: -100,
          width: 28, height: 28,
          borderRadius: '50%',
          background: 'rgba(255, 80, 80, 0.55)',
          border: '2.5px solid rgba(255,255,255,0.85)',
          pointerEvents: 'none',
          zIndex: 9000,
          opacity: 0,
          transition: 'opacity 0.18s ease-out',
          willChange: 'left, top, opacity',
        }} />

        {/* ── 카메라 PiP — 우측 상단 반투명 미리보기 (실제 인식 영역 + 관절) ── */}
        {gestureEnabled && pipEnabled && (
          <div style={{
            position: 'fixed',
            top: 16, right: 16,
            width: 200,
            borderRadius: 10,
            overflow: 'hidden',
            border: '1.5px solid rgba(255,255,255,0.45)',
            boxShadow: '0 4px 18px rgba(0,0,0,0.45)',
            opacity: 0.82,
            background: '#000',
            pointerEvents: 'none',
            zIndex: 9003,
          }}>
            <canvas
              ref={pipCanvasRef}
              style={{ display: 'block', width: '100%', height: 'auto' }}
            />
          </div>
        )}

        {/* ── OK 로딩 링 — DOM 직접 조작 ── */}
        <div ref={okRingRef} style={{
          display: 'none',
          position: 'fixed',
          width: 56, height: 56,
          borderRadius: '50%',
          pointerEvents: 'none',
          zIndex: 9004,
        }}>
          <div style={{
            position: 'absolute', inset: 7,
            borderRadius: '50%',
            background: 'rgba(0,0,0,0.55)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'rgba(255,255,255,0.9)',
            fontSize: 14, fontWeight: 700,
          }}>✓</div>
        </div>

        {/* ── 제스처 라벨 알림 ── */}
        {gestureLabel && (
          <div style={{
            position: 'fixed',
            top: 24, left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(0,0,0,0.72)',
            color: '#fff',
            padding: '8px 22px',
            borderRadius: 24,
            fontSize: 18,
            fontWeight: 600,
            pointerEvents: 'none',
            zIndex: 9001,
          }}>
            {gestureLabel}
          </div>
        )}

        {/* ── 메인 레이아웃 ── */}
        <div style={{
          display: 'flex', flexDirection: 'column',
          height: '100dvh', minHeight: '100vh',
          overflow: 'hidden',
          paddingBottom: CONTROL_BAR_HEIGHT,
        }}>
          <div style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
            {screens[screen] ?? screens.start}
          </div>

          <div style={{
            flexShrink: 0,
            height: chatOpen ? '33vh' : 0,
            overflow: 'hidden',
            transition: 'height 0.35s ease',
            background: '#e0e0e0',
            borderTop: chatOpen ? '1.5px solid #bbb' : 'none',
          }}>
            <ChatPanel
              onClose={() => setChatOpen(false)}
              isOpen={chatOpen}
              cart={cartForLLM}
              screen={screen}
              orderType={orderType}
              modalStateRef={modalStateRef}
              onAction={handleVoiceAction}
            />
          </div>
        </div>

        {/* ── 접근성 컨트롤 바 ── */}
        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0, right: 0,
            zIndex: 500,
            height: CONTROL_BAR_HEIGHT,
            boxSizing: 'border-box',
            background: '#000',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 40,
            fontSize: 14,
          }}
        >
          <ControlText
            onClick={() => setChatOpen(o => !o)}
            ko={`음성인식 ${chatOpen ? 'ON' : 'OFF'}`}
            en={`Voice ${chatOpen ? 'ON' : 'OFF'}`}
          />
          <ControlText
            onClick={() => setGestureEnabled(v => !v)}
            ko={`제스처 ${gestureEnabled ? 'ON' : 'OFF'}`}
            en={`Gesture ${gestureEnabled ? 'ON' : 'OFF'}`}
          />
          <ControlText
            disabled={!gestureEnabled}
            onClick={() => gestureEnabled && setPipEnabled(v => !v)}
            ko={`카메라 ${pipEnabled && gestureEnabled ? 'ON' : 'OFF'}`}
            en={`Camera ${pipEnabled && gestureEnabled ? 'ON' : 'OFF'}`}
          />
        </div>
      </>
  )
}

function ControlText({ onClick, disabled = false, ko, en }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: 'none',
        border: 'none',
        color: disabled ? 'rgba(255,255,255,0.4)' : '#fff',
        cursor: disabled ? 'not-allowed' : 'pointer',
        padding: '4px 0',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        lineHeight: 1.3,
      }}
    >
      <span style={{ fontSize: 15, fontWeight: 700 }}>{ko}</span>
      <span style={{ fontSize: 11, fontWeight: 400, opacity: 0.75 }}>{en}</span>
    </button>
  )
}

export default _isCollect ? CollectTool : function App() {
  return (
    <LocaleProvider>
      <AppContent />
    </LocaleProvider>
  )
}