import { useState } from 'react'
import { DUMMY_PAYMENTS } from '../api/adminApi.js'
import StatusBadge from '../components/StatusBadge.jsx'

const FILTERS = [
  { key: 'all',      label: '전체' },
  { key: 'PENDING',  label: '대기' },
  { key: 'SUCCESS',  label: '완료' },
  { key: 'FAILED',   label: '실패' },
  { key: 'REFUNDED', label: '환불됨' },
]

function RefundModal({ payment, onClose, onConfirm }) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    if (!reason.trim()) { alert('환불 사유를 입력해 주세요'); return }
    setLoading(true)
    await onConfirm(payment.payment_id, reason)
    setLoading(false)
    onClose()
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">환불 처리</div>
        <p style={{ fontSize:'13px', color:'#666', marginBottom:'16px' }}>
          주문 <strong className="order-number">#{payment.order_number}</strong>의 결제
          ({payment.amount.toLocaleString('ko-KR')}원)를 환불합니다.
        </p>
        <div style={{
          background:'#fff8e1', border:'1px solid #ffe082',
          borderRadius:'8px', padding:'10px 14px',
          fontSize:'12px', color:'#795548', marginBottom:'16px'
        }}>
          ⚠️ 환불 시 포인트·쿠폰이 함께 원상복구됩니다. 이 작업은 되돌릴 수 없습니다.
        </div>
        <div className="form-group">
          <label className="form-label">환불 사유</label>
          <input
            className="form-input"
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="예: 고객 변심, 품질 불량 등"
            autoFocus
          />
        </div>
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-danger" onClick={handleConfirm} disabled={loading}>
            {loading ? '처리 중…' : '환불 확인'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function PaymentsPage() {
  const [payments, setPayments] = useState(DUMMY_PAYMENTS)
  const [filter, setFilter] = useState('all')
  const [refundTarget, setRefundTarget] = useState(null)

  const handleRefund = (paymentId, reason) => {
    setPayments(prev => prev.map(p =>
      p.payment_id === paymentId
        ? { ...p, status: 'REFUNDED', failure_reason: reason, refunded_at: new Date().toLocaleTimeString('ko-KR', { hour:'2-digit', minute:'2-digit' }) }
        : p
    ))
  }

  const filtered = payments.filter(p =>
    filter === 'all' || p.status === filter
  )

  return (
    <div>
      {/* Filters */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'16px' }}>
        <div className="filter-chips">
          {FILTERS.map(f => (
            <button
              key={f.key}
              className={`chip${filter === f.key ? ' active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div style={{
          border:'1.5px solid #ddd', borderRadius:'8px', padding:'6px 14px',
          fontSize:'13px', color:'#666', background:'#fff'
        }}>
          2026-07-{String(new Date().getDate()-6).padStart(2,'0')} ~ 07-{String(new Date().getDate()).padStart(2,'0')}
        </div>
      </div>

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>결제ID</th>
              <th>주문번호</th>
              <th>수단</th>
              <th>금액/상태</th>
              <th>실패/환불사유</th>
              <th>결제시각</th>
              <th>환불</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={7} className="loading-text">결제 내역이 없습니다</td></tr>
            )}
            {filtered.map(p => (
              <tr key={p.payment_id}>
                <td style={{ color:'#888', fontSize:'13px' }}>{p.payment_id}</td>
                <td className="order-number">#{p.order_number}</td>
                <td>{p.method}</td>
                <td>
                  <span style={{ marginRight:'8px' }}>{p.amount.toLocaleString('ko-KR')}원</span>
                  <StatusBadge type="payment" value={p.status} />
                </td>
                <td style={{ color: p.failure_reason ? '#c0392b' : '#ccc', fontSize:'13px' }}>
                  {p.failure_reason ?? '–'}
                </td>
                <td style={{ color:'#888', fontSize:'13px' }}>{p.paid_at}</td>
                <td>
                  {p.status === 'SUCCESS' ? (
                    <button
                      className="btn-danger btn-sm"
                      onClick={() => setRefundTarget(p)}
                    >
                      환불
                    </button>
                  ) : (
                    <button className="btn-disabled btn-sm" disabled>환불</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {refundTarget && (
        <RefundModal
          payment={refundTarget}
          onClose={() => setRefundTarget(null)}
          onConfirm={handleRefund}
        />
      )}
    </div>
  )
}
