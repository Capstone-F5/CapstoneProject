import { useState } from 'react'
import { listUsers, getUserDetail, adjustPoints, updateUserTier } from '../api/adminApi.js'
import StatusBadge from '../components/StatusBadge.jsx'

const TIER_COLORS = {
  BASIC:  { bg:'#e8f5e9', color:'#2e7d32' },
  SILVER: { bg:'#e8eaf6', color:'#3949ab' },
  GOLD:   { bg:'#fff8e1', color:'#f57f17' },
  VIP:    { bg:'linear-gradient(135deg,#ff6b6b,#ffd93d,#6bcb77)', color:'#fff' },
}

function TierBadge({ tier }) {
  if (!tier) return <span className="badge badge-inactive">비회원</span>
  const style = TIER_COLORS[tier] ?? { bg:'#f5f5f5', color:'#888' }
  return (
    <span style={{
      display:'inline-block', padding:'2px 10px', borderRadius:'999px',
      fontSize:'12px', fontWeight:'700',
      background: style.bg, color: style.color,
    }}>
      {tier}
    </span>
  )
}

function PointsModal({ user, onClose, onConfirm }) {
  const [delta, setDelta] = useState('')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    const d = parseInt(delta, 10)
    if (isNaN(d) || d === 0) { alert('조정할 포인트 값을 입력해 주세요'); return }
    if (!reason.trim()) { alert('조정 사유를 입력해 주세요'); return }
    setLoading(true)
    try {
      await onConfirm(d, reason)
      onClose()
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">포인트 조정</div>
        <p style={{ fontSize:'13px', color:'#666', marginBottom:'16px' }}>
          <strong>{user.phone_number}</strong> 현재 보유 포인트: <strong>{user.current_points.toLocaleString('ko-KR')}P</strong>
        </p>
        <div className="form-group">
          <label className="form-label">조정값 (양수: 적립, 음수: 차감)</label>
          <input
            className="form-input"
            type="number"
            value={delta}
            onChange={e => setDelta(e.target.value)}
            placeholder="예: 500 (적립) 또는 -200 (차감)"
            autoFocus
          />
        </div>
        <div className="form-group">
          <label className="form-label">조정 사유 <span style={{color:'#e00'}}>*</span></label>
          <input
            className="form-input"
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="예: 이벤트 보상, 운영자 수동 조정 등"
          />
        </div>
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleConfirm} disabled={loading}>
            {loading ? '저장 중…' : '확인'}
          </button>
        </div>
      </div>
    </div>
  )
}

function TierModal({ user, onClose, onConfirm }) {
  const [tier, setTier] = useState(user.tier ?? 'BASIC')
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await onConfirm(tier)
      onClose()
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">회원 등급 변경</div>
        <p style={{ fontSize:'13px', color:'#666', marginBottom:'16px' }}>
          <strong>{user.phone_number}</strong> &nbsp; 현재 등급: <TierBadge tier={user.tier} />
        </p>
        <div className="form-group">
          <label className="form-label">변경할 등급</label>
          <select className="form-input" value={tier} onChange={e => setTier(e.target.value)}>
            <option value="BASIC">BASIC</option>
            <option value="SILVER">SILVER</option>
            <option value="GOLD">GOLD</option>
          </select>
        </div>
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleConfirm} disabled={loading}>
            {loading ? '변경 중…' : '변경'}
          </button>
        </div>
      </div>
    </div>
  )
}

function UserDetail({ user, onPointsAdjust, onTierChange }) {
  if (!user) return null

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'16px' }}>
      {/* Points card */}
      <div className="card">
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'4px' }}>
          <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
            <span style={{ fontWeight:'700', fontSize:'16px' }}>{user.phone_number ?? '알 수 없음'}</span>
            <TierBadge tier={user.tier} />
            {!user.is_guest && (
              <button className="btn-outline btn-sm" style={{ fontSize:11 }} onClick={onTierChange}>
                등급 변경
              </button>
            )}
          </div>
          <span style={{ fontSize:'12px', color:'#aaa' }}>
            가입일 {user.created_at ? new Date(user.created_at).toLocaleDateString('ko-KR', { year:'numeric', month:'2-digit', day:'2-digit' }).replace(/\. /g,'.').replace('.','/').replace('.','/') : '–'}
          </span>
        </div>
        <div style={{ marginTop:'14px', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
          <div>
            <div style={{ fontSize:'12px', color:'#aaa', marginBottom:'4px' }}>현재 포인트</div>
            <div style={{ fontSize:'26px', fontWeight:'700', color:'#744032' }}>
              {user.current_points.toLocaleString('ko-KR')} P
            </div>
          </div>
          <button className="btn-primary" onClick={onPointsAdjust}>포인트 조정</button>
        </div>
      </div>

      {/* Recent orders */}
      {user.recent_orders?.length > 0 && (
        <div className="card">
          <div style={{ fontWeight:'700', fontSize:'14px', marginBottom:'14px' }}>최근 주문 내역</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>주문번호</th>
                <th>유형</th>
                <th>상태</th>
                <th>결제</th>
                <th style={{ textAlign:'right' }}>금액(생성시각)</th>
              </tr>
            </thead>
            <tbody>
              {user.recent_orders.map(order => (
                <tr key={order.order_id}>
                  <td className="order-number">#{order.order_number}</td>
                  <td>{order.order_type === 'EAT_IN' ? '매장' : '포장'}</td>
                  <td><StatusBadge value={order.status} /></td>
                  <td>
                    {order.payment_status
                      ? <StatusBadge type="payment" value={order.payment_status} />
                      : <span style={{ color:'#ccc', fontSize:12 }}>–</span>}
                  </td>
                  <td style={{ textAlign:'right' }}>
                    <span style={{ fontWeight:'500' }}>{order.final_amount.toLocaleString('ko-KR')}원</span>
                    <span style={{ color:'#bbb', marginLeft:'6px', fontSize:'11px' }}>
                      {order.created_at ? new Date(order.created_at).toLocaleTimeString('ko-KR', { hour:'2-digit', minute:'2-digit' }) : ''}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Coupons */}
      {user.coupons?.length > 0 && (
        <div className="card">
          <div style={{ fontWeight:'700', fontSize:'14px', marginBottom:'14px' }}>보유 쿠폰</div>
          <div style={{ display:'flex', gap:'8px', flexWrap:'wrap' }}>
            {user.coupons.map(uc => (
              <span key={uc.user_coupon_id} style={{
                display:'inline-block', padding:'5px 12px',
                border:'1px solid #ddd', borderRadius:'8px',
                fontSize:'12px', color:'#444',
                background: uc.is_used ? '#f5f5f5' : '#fff',
              }}>
                쿠폰 {uc.coupon_id?.slice(0,8)}
                {uc.is_used && <span style={{ color:'#bbb', marginLeft:'4px' }}>(사용됨)</span>}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function UsersPage() {
  const [phone, setPhone] = useState('')
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState(null)
  const [detailUser, setDetailUser] = useState(null)
  const [searching, setSearching] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [showPointsModal, setShowPointsModal] = useState(false)
  const [showTierModal,   setShowTierModal]   = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async () => {
    setError('')
    setSearching(true)
    try {
      const data = await listUsers(phone || undefined)
      setUsers(data)
      setSelectedUser(null)
      setDetailUser(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setSearching(false)
    }
  }

  const handleSelectUser = async (user) => {
    setSelectedUser(user)
    setDetailUser(null)
    setLoadingDetail(true)
    try {
      const detail = await getUserDetail(user.id)
      setDetailUser(detail)
    } catch (e) {
      // fallback: show basic info
      setDetailUser({ ...user, recent_orders: [], coupons: [] })
    } finally {
      setLoadingDetail(false)
    }
  }

  const handlePointsAdjust = async (delta, reason) => {
    if (!selectedUser) return
    const updated = await adjustPoints(selectedUser.id, delta, reason)
    setDetailUser(prev => prev ? { ...prev, current_points: updated.current_points } : prev)
    setUsers(prev => prev.map(u => u.id === selectedUser.id ? { ...u, current_points: updated.current_points } : u))
  }

  const handleTierUpdate = async (tier) => {
    if (!selectedUser) return
    const updated = await updateUserTier(selectedUser.id, tier)
    setDetailUser(prev => prev ? { ...prev, tier: updated.tier } : prev)
    setUsers(prev => prev.map(u => u.id === selectedUser.id ? { ...u, tier: updated.tier } : u))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <div style={{ display:'flex', gap:'16px', alignItems:'flex-start' }}>
      {/* Left: search + list */}
      <div style={{ width:300, minWidth:300, display:'flex', flexDirection:'column', gap:'12px' }}>
        {/* Search */}
        <div style={{ display:'flex', gap:'8px' }}>
          <input
            className="form-input"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="전화번호 입력"
            style={{ flex:1 }}
          />
          <button
            className="btn-primary"
            onClick={handleSearch}
            disabled={searching}
            style={{ whiteSpace:'nowrap' }}
          >
            {searching ? '…' : '검색'}
          </button>
        </div>

        {error && <div style={{ color:'#c00', fontSize:'13px' }}>{error}</div>}

        {/* User list */}
        <div className="card" style={{ padding:'8px 0', minHeight:120 }}>
          {users.length === 0 && !searching && (
            <div className="loading-text" style={{ padding:'24px 0' }}>
              전화번호로 검색하세요
            </div>
          )}
          {users.map(user => (
            <div
              key={user.id}
              onClick={() => handleSelectUser(user)}
              style={{
                padding:'12px 16px',
                cursor:'pointer',
                background: selectedUser?.id === user.id ? '#fff5f0' : 'transparent',
                borderLeft: selectedUser?.id === user.id ? '3px solid #744032' : '3px solid transparent',
              }}
            >
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'3px' }}>
                <span style={{ fontWeight:'600', fontSize:'14px' }}>{user.phone_number ?? '비회원'}</span>
                <TierBadge tier={user.tier} />
              </div>
              <div style={{ fontSize:'12px', color:'#999' }}>
                포인트 {user.current_points.toLocaleString('ko-KR')}P
                {user.created_at && (
                  <span style={{ marginLeft:'8px' }}>
                    · 가입일 {new Date(user.created_at).toLocaleDateString('ko-KR')}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right: detail */}
      <div style={{ flex:1, minWidth:0 }}>
        {loadingDetail && <div className="loading-text">회원 정보 로딩 중…</div>}
        {!loadingDetail && !detailUser && (
          <div className="loading-text">회원을 검색하고 선택하세요</div>
        )}
        {!loadingDetail && detailUser && (
          <UserDetail
            user={detailUser}
            onPointsAdjust={() => setShowPointsModal(true)}
            onTierChange={() => setShowTierModal(true)}
          />
        )}
      </div>

      {showPointsModal && detailUser && (
        <PointsModal
          user={detailUser}
          onClose={() => setShowPointsModal(false)}
          onConfirm={handlePointsAdjust}
        />
      )}

      {showTierModal && detailUser && (
        <TierModal
          user={detailUser}
          onClose={() => setShowTierModal(false)}
          onConfirm={handleTierUpdate}
        />
      )}
    </div>
  )
}
