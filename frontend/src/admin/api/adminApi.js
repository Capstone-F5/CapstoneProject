const API_BASE = import.meta.env.VITE_API_URL ?? ''

function getToken() {
  return localStorage.getItem('admin_token') ?? ''
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
  }
}

async function req(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: authHeaders(),
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '서버 오류가 발생했습니다' }))
    throw new Error(err.detail ?? '오류가 발생했습니다')
  }
  return res.json()
}

// ── Auth ──────────────────────────────────────────────
export async function login(username, password) {
  const res = await fetch(`${API_BASE}/api/admin/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? '로그인에 실패했습니다')
  }
  return res.json()  // { access_token, expires_in }
}

export async function getMe() {
  return req('GET', '/api/admin/auth/me')
}

export async function logout() {
  await fetch(`${API_BASE}/api/admin/auth/logout`, { method: 'POST', headers: authHeaders() }).catch(() => {})
  localStorage.removeItem('admin_token')
}

// ── Menu (Real API) ───────────────────────────────────
export async function fetchAdminMenu() {
  // 관리자 전용 엔드포인트: 숨김 카테고리도 포함
  const res = await fetch(`${API_BASE}/api/admin/menu`, {
    headers: { 'Authorization': `Bearer ${getToken()}` },
  })
  if (!res.ok) throw new Error('메뉴 로드 실패')
  return res.json()
}

export async function createCategory(payload) {
  return req('POST', '/api/admin/categories', payload)
}

export async function updateCategory(id, payload) {
  return req('PATCH', `/api/admin/categories/${id}`, payload)
}

export async function deleteCategory(id) {
  return req('DELETE', `/api/admin/categories/${id}`)
}

export async function createMenuItem(payload) {
  return req('POST', '/api/admin/menu/items', payload)
}

export async function updateMenuItem(id, payload) {
  return req('PATCH', `/api/admin/menu/items/${id}`, payload)
}

export async function deleteMenuItem(id) {
  return req('DELETE', `/api/admin/menu/items/${id}`)
}

export async function uploadMenuImage(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/api/admin/upload/image`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${getToken()}` },
    body: fd,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '업로드 실패' }))
    throw new Error(err.detail ?? '업로드 실패')
  }
  return res.json()  // { url }
}

export async function createMenuOption(itemId, payload) {
  return req('POST', `/api/admin/menu/items/${itemId}/options`, payload)
}

export async function updateMenuOption(itemId, optionId, payload) {
  return req('PATCH', `/api/admin/menu/items/${itemId}/options/${optionId}`, payload)
}

export async function deleteMenuOption(itemId, optionId) {
  return req('DELETE', `/api/admin/menu/items/${itemId}/options/${optionId}`)
}

// ── Users (Real API) ─────────────────────────────────
export async function listUsers(phone) {
  const q = phone ? `?phone=${encodeURIComponent(phone)}` : ''
  return req('GET', `/api/admin/users${q}`)
}

export async function getUserDetail(id) {
  return req('GET', `/api/admin/users/${id}`)
}

export async function adjustPoints(id, delta, reason) {
  return req('PATCH', `/api/admin/users/${id}/points`, { delta, reason })
}

export async function updateUserTier(id, tier) {
  return req('PATCH', `/api/admin/users/${id}/tier`, { tier })
}

// ── Orders (Real API) ────────────────────────────────
export async function fetchAdminOrders(status) {
  const q = status ? `?status=${encodeURIComponent(status)}` : ''
  return req('GET', `/api/admin/orders${q}`)
}

export async function updateOrderStatus(orderId, status) {
  return req('PATCH', `/api/admin/orders/${orderId}/status?status=${encodeURIComponent(status)}`)
}

// ── Payments (Real API) ───────────────────────────────
export async function fetchAdminPayments(status) {
  const q = status ? `?status=${encodeURIComponent(status)}` : ''
  return req('GET', `/api/admin/payments${q}`)
}

export async function refundPayment(id, reason) {
  return req('POST', `/api/admin/payments/${id}/refund`, { reason })
}

// ── Stats (Real API) ─────────────────────────────────
export async function fetchStatsSummary() {
  return req('GET', '/api/admin/stats/summary')
}

export async function fetchSalesSeries(range = '7d') {
  return req('GET', `/api/admin/stats/sales?range=${range}`)
}

export async function fetchPopularItems(range = '7d') {
  return req('GET', `/api/admin/stats/popular-items?range=${range}`)
}

export async function fetchCategorySales(range = '7d') {
  return req('GET', `/api/admin/stats/category-sales?range=${range}`)
}

export async function fetchPaymentMethodStats(range = '7d') {
  return req('GET', `/api/admin/stats/payment-methods?range=${range}`)
}

// ── Coupons (Real API) ────────────────────────────────
export async function fetchAdminCoupons() {
  return req('GET', '/api/admin/coupons')
}

export async function createCoupon(payload) {
  return req('POST', '/api/admin/coupons', payload)
}

export async function issueCoupon(couponId, phone) {
  return req('POST', `/api/admin/coupons/${couponId}/issue`, { phone })
}

export async function toggleCoupon(id) {
  return req('PATCH', `/api/admin/coupons/${id}/toggle`)
}

export async function deleteCoupon(id) {
  return req('DELETE', `/api/admin/coupons/${id}`)
}

// ── Discounts (Real API) ──────────────────────────────
export async function fetchAdminDiscounts() {
  return req('GET', '/api/admin/discounts')
}

export async function createDiscount(payload) {
  return req('POST', '/api/admin/discounts', payload)
}

export async function toggleDiscount(id) {
  return req('PATCH', `/api/admin/discounts/${id}/toggle`)
}

export async function deleteDiscount(id) {
  return req('DELETE', `/api/admin/discounts/${id}`)
}

// ── Legacy dummy stubs (하위호환) ──────────────────────
const now = new Date()
function t(h, m) {
  const d = new Date(now)
  d.setHours(h, m, 0, 0)
  return d.toISOString()
}

export const DUMMY_ORDERS = [
  { order_id:'ord-001', order_number:'1042', order_type:'EAT_IN',  status:'RECEIVED',  table_number:3,    subtotal:12000, discount_amount:0,    final_amount:12000, points_used:0,    points_earned:600,  created_at:t(14,31), payment_status:'SUCCESS',
    items:[{name_ko:'F버거 세트',     quantity:1, unit_price:10000, total_price:10000, selected_options:['세트 변경 +2,000원','양념 감자튀김 +500원','콜라 +0원'], special_note:'양파 제외'},
           {name_ko:'게살버거',       quantity:1, unit_price:5000,  total_price:5000,  selected_options:[], special_note:'제외 없음'}]},
  { order_id:'ord-002', order_number:'1041', order_type:'TAKE_OUT', status:'COOKING',   table_number:null, subtotal:14200, discount_amount:0,    final_amount:14200, points_used:0,    points_earned:710,  created_at:t(14,28), payment_status:'SUCCESS',
    items:[{name_ko:'불고기버거 세트', quantity:1, unit_price:9500,  total_price:9500,  selected_options:[], special_note:null},
           {name_ko:'치즈버거',       quantity:1, unit_price:4700,  total_price:4700,  selected_options:[], special_note:null}]},
  { order_id:'ord-003', order_number:'1040', order_type:'EAT_IN',  status:'COOKING',   table_number:7,    subtotal:6800,  discount_amount:0,    final_amount:6800,  points_used:0,    points_earned:340,  created_at:t(14,22), payment_status:'SUCCESS',
    items:[{name_ko:'비건버거',       quantity:1, unit_price:6800,  total_price:6800,  selected_options:[], special_note:null}]},
  { order_id:'ord-004', order_number:'1039', order_type:'EAT_IN',  status:'COOKING',   table_number:2,    subtotal:11000, discount_amount:0,    final_amount:11000, points_used:0,    points_earned:550,  created_at:t(14,17), payment_status:'SUCCESS',
    items:[{name_ko:'더블불고기버거', quantity:1, unit_price:11000, total_price:11000, selected_options:[], special_note:null}]},
  { order_id:'ord-005', order_number:'1038', order_type:'EAT_IN',  status:'CANCELLED', table_number:5,    subtotal:11000, discount_amount:0,    final_amount:11000, points_used:0,    points_earned:0,    created_at:t(14,16), payment_status:'REFUNDED',
    items:[{name_ko:'치킨가슴살버거 세트', quantity:1, unit_price:11000, total_price:11000, selected_options:[], special_note:null}]},
  { order_id:'ord-006', order_number:'1037', order_type:'TAKE_OUT', status:'READY',    table_number:null, subtotal:7500,  discount_amount:0,    final_amount:7500,  points_used:0,    points_earned:375,  created_at:t(14,11), payment_status:'SUCCESS',
    items:[{name_ko:'새우버거 세트',  quantity:1, unit_price:7500,  total_price:7500,  selected_options:[], special_note:null}]},
  { order_id:'ord-007', order_number:'1036', order_type:'TAKE_OUT', status:'COMPLETED', table_number:null, subtotal:10500, discount_amount:0,    final_amount:10500, points_used:0,    points_earned:525,  created_at:t(14,8),  payment_status:'SUCCESS',
    items:[{name_ko:'모짜렐라버거 세트', quantity:1, unit_price:10500, total_price:10500, selected_options:[], special_note:null}]},
  { order_id:'ord-008', order_number:'1035', order_type:'EAT_IN',  status:'COMPLETED', table_number:1,    subtotal:5500,  discount_amount:0,    final_amount:5500,  points_used:0,    points_earned:275,  created_at:t(14,2),  payment_status:'SUCCESS',
    items:[{name_ko:'불고기버거',     quantity:1, unit_price:5500,  total_price:5500,  selected_options:[], special_note:null}]},
  { order_id:'ord-009', order_number:'1034', order_type:'TAKE_OUT', status:'CANCELLED', table_number:null, subtotal:17500, discount_amount:0,    final_amount:17500, points_used:0,    points_earned:0,    created_at:t(13,56), payment_status:'FAILED',
    items:[{name_ko:'데리버거 세트',  quantity:2, unit_price:8750,  total_price:17500, selected_options:[], special_note:null}]},
  { order_id:'ord-010', order_number:'1033', order_type:'EAT_IN',  status:'COMPLETED', table_number:4,    subtotal:9800,  discount_amount:1000, final_amount:8800,  points_used:1000, points_earned:440,  created_at:t(13,49), payment_status:'SUCCESS',
    items:[{name_ko:'그릴드비프버거', quantity:1, unit_price:9800,  total_price:9800,  selected_options:[], special_note:null}]},
]

// ── Payments (Dummy) ──────────────────────────────────
export const DUMMY_PAYMENTS = [
  { payment_id:'P2052', order_number:'1043', method:'네이버페이', amount:5600,  status:'PENDING',  failure_reason:null,          paid_at:'14:32', refunded_at:null },
  { payment_id:'P2051', order_number:'1042', method:'카드',      amount:12000, status:'SUCCESS',  failure_reason:null,          paid_at:'14:31', refunded_at:null },
  { payment_id:'P2050', order_number:'1041', method:'카드',      amount:14200, status:'SUCCESS',  failure_reason:null,          paid_at:'14:28', refunded_at:null },
  { payment_id:'P2049', order_number:'1040', method:'카드',      amount:6800,  status:'SUCCESS',  failure_reason:null,          paid_at:'14:22', refunded_at:null },
  { payment_id:'P2048', order_number:'1039', method:'현금',      amount:11000, status:'SUCCESS',  failure_reason:null,          paid_at:'14:17', refunded_at:null },
  { payment_id:'P2047', order_number:'1038', method:'카드',      amount:11000, status:'REFUNDED', failure_reason:'고객 변심',    paid_at:'14:16', refunded_at:'14:20' },
  { payment_id:'P2046', order_number:'1037', method:'삼성페이',  amount:7500,  status:'SUCCESS',  failure_reason:null,          paid_at:'14:11', refunded_at:null },
  { payment_id:'P2045', order_number:'1036', method:'카드',      amount:10500, status:'SUCCESS',  failure_reason:null,          paid_at:'14:08', refunded_at:null },
  { payment_id:'P2044', order_number:'1035', method:'카드',      amount:5500,  status:'SUCCESS',  failure_reason:null,          paid_at:'14:02', refunded_at:null },
  { payment_id:'P2043', order_number:'1034', method:'카드',      amount:17500, status:'FAILED',   failure_reason:'한도 초과',    paid_at:'13:56', refunded_at:null },
]

// ── Stats (Dummy) ─────────────────────────────────────
export const DUMMY_STATS = {
  summary: { today_sales: 1284500, order_count: 147, avg_order_value: 8738 },
  sales_7d: [
    { date:'7/25', sales:920000,  order_count:105 },
    { date:'7/26', sales:1050000, order_count:120 },
    { date:'7/27', sales:870000,  order_count:98  },
    { date:'7/28', sales:1100000, order_count:128 },
    { date:'7/29', sales:980000,  order_count:112 },
    { date:'7/30', sales:1180000, order_count:135 },
    { date:'7/31', sales:1284500, order_count:147 },
  ],
  sales_30d: Array.from({length:30}, (_,i) => ({
    date: `7/${i+1}`,
    sales: 700000 + Math.round(Math.sin(i*0.4)*200000 + i*18000),
    order_count: 80 + Math.round(Math.sin(i*0.4)*25 + i*2),
  })),
  popular_items: [
    { menu_item_id:'1', name_ko:'F버거 세트',       quantity_sold:312, revenue:3120000 },
    { menu_item_id:'2', name_ko:'불고기버거 세트',   quantity_sold:289, revenue:2745500 },
    { menu_item_id:'3', name_ko:'치즈버거',          quantity_sold:241, revenue:1132700 },
    { menu_item_id:'4', name_ko:'새우버거 세트',     quantity_sold:198, revenue:1485000 },
    { menu_item_id:'5', name_ko:'비건버거',          quantity_sold:156, revenue:1060800 },
  ],
}

// ── Coupons (Dummy) ───────────────────────────────────
export const DUMMY_COUPONS = [
  { id:'cp1', code:'WELCOME3000', discount_type:'CASH',    discount_value:3000, min_order_amount:5000,  used_count:142, max_usage_count:1000, valid_until:'~08.01', is_active:true },
  { id:'cp2', code:'SALE10',     discount_type:'PERCENT',  discount_value:15,   min_order_amount:10000, used_count:12,  max_usage_count:150,  valid_until:'~08.01', is_active:true },
  { id:'cp3', code:'SUMMER500',  discount_type:'CASH',    discount_value:3000, min_order_amount:5000,  used_count:13,  max_usage_count:500,  valid_until:'~06.30', is_active:false },
]

export const DUMMY_DISCOUNTS = [
  { id:'dc1', name_ko:'여름 버거 할인',  target_type:'CATEGORY', discount_type:'CASH',    discount_value:3000, applicable_tier:'ALL',  valid_until:'~08.01', is_active:true },
  { id:'dc2', name_ko:'VIP 전메뉴 할인', target_type:'ALL',      discount_type:'PERCENT',  discount_value:15,   applicable_tier:'GOLD', valid_until:'~08.01', is_active:true },
  { id:'dc3', name_ko:'F버거 할인',      target_type:'MENU',     discount_type:'CASH',    discount_value:3000, applicable_tier:'ALL',  valid_until:'~04.12', is_active:false },
]
