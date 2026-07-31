import { useState } from 'react'
import { DUMMY_COUPONS, DUMMY_DISCOUNTS } from '../api/adminApi.js'

const TARGET_LABELS = { MENU: '메뉴', CATEGORY: '카테고리', ALL: '전체' }
const TIER_LABELS = { ALL: '전체 회원', STUDENT: '학생', SENIOR: '시니어', GOLD: 'VIP' }

function CouponModal({ onClose, onSave }) {
  const [form, setForm] = useState({ code:'', discount_type:'CASH', discount_value:'', min_order_amount:'', max_usage_count:'' })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.code || !form.discount_value) { alert('코드와 할인값을 입력해 주세요'); return }
    setLoading(true)
    await onSave(form)
    setLoading(false)
    onClose()
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">쿠폰 생성</div>
        <div className="form-group">
          <label className="form-label">쿠폰 코드</label>
          <input className="form-input" value={form.code} onChange={e => set('code', e.target.value.toUpperCase())} placeholder="예: SUMMER2026" />
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px' }}>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">할인 유형</label>
            <select className="form-input" value={form.discount_type} onChange={e => set('discount_type', e.target.value)}>
              <option value="CASH">정액</option>
              <option value="PERCENT">정률</option>
            </select>
          </div>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">할인값 ({form.discount_type === 'CASH' ? '원' : '%'})</label>
            <input className="form-input" type="number" value={form.discount_value} onChange={e => set('discount_value', e.target.value)} />
          </div>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginTop:'12px' }}>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">최소 주문금액 (원)</label>
            <input className="form-input" type="number" value={form.min_order_amount} onChange={e => set('min_order_amount', e.target.value)} placeholder="0 = 제한없음" />
          </div>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">최대 사용 횟수</label>
            <input className="form-input" type="number" value={form.max_usage_count} onChange={e => set('max_usage_count', e.target.value)} placeholder="0 = 무제한" />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleSave} disabled={loading}>{loading ? '생성 중…' : '생성'}</button>
        </div>
      </div>
    </div>
  )
}

function DiscountModal({ onClose, onSave }) {
  const [form, setForm] = useState({ name_ko:'', target_type:'ALL', discount_type:'CASH', discount_value:'', applicable_tier:'ALL' })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.name_ko || !form.discount_value) { alert('이름과 할인값을 입력해 주세요'); return }
    setLoading(true)
    await onSave(form)
    setLoading(false)
    onClose()
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">할인 생성</div>
        <div className="form-group">
          <label className="form-label">할인 이름</label>
          <input className="form-input" value={form.name_ko} onChange={e => set('name_ko', e.target.value)} placeholder="예: 여름 특별 할인" />
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px' }}>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">적용 대상</label>
            <select className="form-input" value={form.target_type} onChange={e => set('target_type', e.target.value)}>
              <option value="ALL">전체</option>
              <option value="CATEGORY">카테고리</option>
              <option value="MENU">메뉴</option>
            </select>
          </div>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">적용 등급</label>
            <select className="form-input" value={form.applicable_tier} onChange={e => set('applicable_tier', e.target.value)}>
              <option value="ALL">전체 회원</option>
              <option value="STUDENT">학생</option>
              <option value="SENIOR">시니어</option>
              <option value="GOLD">VIP</option>
            </select>
          </div>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'12px', marginTop:'12px' }}>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">할인 유형</label>
            <select className="form-input" value={form.discount_type} onChange={e => set('discount_type', e.target.value)}>
              <option value="CASH">정액</option>
              <option value="PERCENT">정률</option>
            </select>
          </div>
          <div className="form-group" style={{ marginBottom:0 }}>
            <label className="form-label">할인값 ({form.discount_type === 'CASH' ? '원' : '%'})</label>
            <input className="form-input" type="number" value={form.discount_value} onChange={e => set('discount_value', e.target.value)} />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleSave} disabled={loading}>{loading ? '생성 중…' : '생성'}</button>
        </div>
      </div>
    </div>
  )
}

function IssueModal({ onClose, onIssue }) {
  const [phone, setPhone] = useState('')
  const [couponCode, setCouponCode] = useState('')
  const [loading, setLoading] = useState(false)

  const handleIssue = async () => {
    if (!phone || !couponCode) { alert('전화번호와 쿠폰 코드를 입력해 주세요'); return }
    setLoading(true)
    await onIssue(phone, couponCode)
    setLoading(false)
    onClose()
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">회원에게 쿠폰 발급</div>
        <div className="form-group">
          <label className="form-label">전화번호</label>
          <input className="form-input" value={phone} onChange={e => setPhone(e.target.value)} placeholder="010-0000-0000" />
        </div>
        <div className="form-group">
          <label className="form-label">쿠폰 코드</label>
          <input className="form-input" value={couponCode} onChange={e => setCouponCode(e.target.value.toUpperCase())} placeholder="예: WELCOME3000" />
        </div>
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleIssue} disabled={loading}>{loading ? '발급 중…' : '발급'}</button>
        </div>
      </div>
    </div>
  )
}

export default function CouponsPage() {
  const [tab, setTab] = useState('coupon')
  const [couponFilter, setCouponFilter] = useState('all')
  const [discountFilter, setDiscountFilter] = useState('all')
  const [coupons, setCoupons] = useState(DUMMY_COUPONS)
  const [discounts, setDiscounts] = useState(DUMMY_DISCOUNTS)
  const [showCouponModal, setShowCouponModal] = useState(false)
  const [showDiscountModal, setShowDiscountModal] = useState(false)
  const [showIssueModal, setShowIssueModal] = useState(false)

  const handleCreateCoupon = (form) => {
    const nc = {
      id: `cp${Date.now()}`,
      code: form.code,
      discount_type: form.discount_type,
      discount_value: Number(form.discount_value),
      min_order_amount: Number(form.min_order_amount) || 0,
      used_count: 0,
      max_usage_count: Number(form.max_usage_count) || 0,
      valid_until: '–',
      is_active: true,
    }
    setCoupons(prev => [nc, ...prev])
  }

  const handleCreateDiscount = (form) => {
    const nd = {
      id: `dc${Date.now()}`,
      name_ko: form.name_ko,
      target_type: form.target_type,
      discount_type: form.discount_type,
      discount_value: Number(form.discount_value),
      applicable_tier: form.applicable_tier,
      valid_until: '–',
      is_active: true,
    }
    setDiscounts(prev => [nd, ...prev])
  }

  const toggleCouponActive = (id) => {
    setCoupons(prev => prev.map(c => c.id === id ? { ...c, is_active: !c.is_active } : c))
  }

  const toggleDiscountActive = (id) => {
    setDiscounts(prev => prev.map(d => d.id === id ? { ...d, is_active: !d.is_active } : d))
  }

  const filteredCoupons = coupons.filter(c =>
    couponFilter === 'all' || (couponFilter === 'active' ? c.is_active : !c.is_active)
  )
  const filteredDiscounts = discounts.filter(d =>
    discountFilter === 'all' || (discountFilter === 'active' ? d.is_active : !d.is_active)
  )

  return (
    <div>
      {/* Tab */}
      <div style={{ display:'flex', gap:'0', marginBottom:'20px', borderBottom:'2px solid #eee' }}>
        {[['coupon','쿠폰'], ['discount','할인']].map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            style={{
              padding:'10px 24px', border:'none', background:'none', cursor:'pointer',
              fontFamily:'Pretendard,sans-serif', fontSize:'15px', fontWeight: tab===k ? '700' : '400',
              color: tab===k ? '#744032' : '#888',
              borderBottom: tab===k ? '2px solid #744032' : '2px solid transparent',
              marginBottom:'-2px',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Coupon tab */}
      {tab === 'coupon' && (
        <div>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'16px' }}>
            <div className="filter-chips">
              {[['all','전체'],['active','활성'],['inactive','비활성']].map(([k,l]) => (
                <button key={k} className={`chip${couponFilter===k?' active':''}`} onClick={() => setCouponFilter(k)}>{l}</button>
              ))}
            </div>
            <div style={{ display:'flex', gap:'8px' }}>
              <button className="btn-outline" onClick={() => setShowIssueModal(true)}>회원에게 발급</button>
              <button className="btn-primary" onClick={() => setShowCouponModal(true)}>+ 쿠폰 생성</button>
            </div>
          </div>
          <div className="card" style={{ padding:0, overflow:'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>코드</th>
                  <th>유형</th>
                  <th>할인값</th>
                  <th>최소주문</th>
                  <th>사용/최대</th>
                  <th>유효기한</th>
                  <th>활성</th>
                  <th style={{width:50}}></th>
                </tr>
              </thead>
              <tbody>
                {filteredCoupons.length === 0 && <tr><td colSpan={8} className="loading-text">쿠폰이 없습니다</td></tr>}
                {filteredCoupons.map(c => (
                  <tr key={c.id} style={{ color: c.is_active ? '#222' : '#bbb' }}>
                    <td style={{ fontWeight:'600', fontFamily:'monospace', letterSpacing:'0.5px' }}>{c.code}</td>
                    <td>{c.discount_type === 'CASH' ? '정액' : '정률'}</td>
                    <td style={{ fontWeight:'600' }}>
                      {c.discount_type === 'CASH'
                        ? `${c.discount_value.toLocaleString('ko-KR')}원`
                        : `${c.discount_value}%`}
                    </td>
                    <td>{c.min_order_amount ? `${c.min_order_amount.toLocaleString('ko-KR')}원` : '–'}</td>
                    <td>{c.used_count}/{c.max_usage_count || '∞'}</td>
                    <td style={{ fontSize:'13px', color:'#888' }}>{c.valid_until}</td>
                    <td>
                      <span className={`badge ${c.is_active ? 'badge-active' : 'badge-inactive'}`}>
                        {c.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td>
                      <button className="btn-outline btn-sm" onClick={() => toggleCouponActive(c.id)}>
                        {c.is_active ? '비활성화' : '활성화'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Discount tab */}
      {tab === 'discount' && (
        <div>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'16px' }}>
            <div className="filter-chips">
              {[['all','전체'],['active','활성'],['inactive','비활성']].map(([k,l]) => (
                <button key={k} className={`chip${discountFilter===k?' active':''}`} onClick={() => setDiscountFilter(k)}>{l}</button>
              ))}
            </div>
            <button className="btn-primary" onClick={() => setShowDiscountModal(true)}>+ 할인 생성</button>
          </div>
          <div className="card" style={{ padding:0, overflow:'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>이름</th>
                  <th>적용대상</th>
                  <th>유형</th>
                  <th>할인값</th>
                  <th>적용등급</th>
                  <th>유효기한</th>
                  <th>활성</th>
                  <th style={{width:50}}></th>
                </tr>
              </thead>
              <tbody>
                {filteredDiscounts.length === 0 && <tr><td colSpan={8} className="loading-text">할인이 없습니다</td></tr>}
                {filteredDiscounts.map(d => (
                  <tr key={d.id} style={{ color: d.is_active ? '#222' : '#bbb' }}>
                    <td style={{ fontWeight:'500' }}>{d.name_ko}</td>
                    <td>
                      <span style={{ border:'1px solid #ddd', borderRadius:'999px', padding:'2px 8px', fontSize:'12px' }}>
                        {TARGET_LABELS[d.target_type] ?? d.target_type}
                      </span>
                    </td>
                    <td>{d.discount_type === 'CASH' ? '정액' : '정률'}</td>
                    <td style={{ fontWeight:'600' }}>
                      {d.discount_type === 'CASH'
                        ? `${d.discount_value.toLocaleString('ko-KR')}원`
                        : `${d.discount_value}%`}
                    </td>
                    <td style={{ fontSize:'13px', color:'#888' }}>{TIER_LABELS[d.applicable_tier] ?? d.applicable_tier}</td>
                    <td style={{ fontSize:'13px', color:'#888' }}>{d.valid_until}</td>
                    <td>
                      <span className={`badge ${d.is_active ? 'badge-active' : 'badge-inactive'}`}>
                        {d.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td>
                      <button className="btn-outline btn-sm" onClick={() => toggleDiscountActive(d.id)}>
                        {d.is_active ? '비활성화' : '활성화'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showCouponModal   && <CouponModal   onClose={() => setShowCouponModal(false)}   onSave={handleCreateCoupon} />}
      {showDiscountModal && <DiscountModal  onClose={() => setShowDiscountModal(false)} onSave={handleCreateDiscount} />}
      {showIssueModal    && <IssueModal     onClose={() => setShowIssueModal(false)}    onIssue={async (p,c) => { alert(`${p}에게 ${c} 쿠폰을 발급했습니다 (더미)`) }} />}
    </div>
  )
}
