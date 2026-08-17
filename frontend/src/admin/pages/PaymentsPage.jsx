import { useState, useEffect } from 'react'
import { fetchAdminPayments, refundPayment } from '../api/adminApi.js'
import StatusBadge from '../components/StatusBadge.jsx'

const FILTERS = [
  { key: 'all',      label: '전체' },
  { key: 'SUCCESS',  label: '완료' },
  { key: 'FAILED',   label: '실패' },
  { key: 'REFUNDED', label: '환불됨' },
]

function fmtDatetime(dt) {
  if (!dt) return '–'
  // 과거 데이터의 timezone 없는 ISO 문자열도 UTC로 간주해 KST로 표시한다.
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/i.test(dt) ? dt : `${dt}Z`
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return '–'
  const parts = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(d).reduce((result, part) => ({ ...result, [part.type]: part.value }), {})
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`
}

function RefundModal({ payment, onClose, onConfirm }) {
  const [reason, setReason]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    if (!reason.trim()) { alert('환불 사유를 입력해 주세요'); return }
    setLoading(true)
    try {
      await onConfirm(payment.payment_id, reason)
      onClose()
    } catch (e) {
      alert(`환불 실패: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <div className="modal-title">환불 처리</div>
        <p style={{ fontSize:'13px', color:'#666', marginBottom:'16px' }}>
          주문 <strong className="order-number">#{payment.order_number}</strong>의 결제
          ({Number(payment.amount).toLocaleString('ko-KR')}원)를 환불합니다.
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
  const [payments,     setPayments]     = useState([])
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState('')
  const [filter,       setFilter]       = useState('all')
  const [refundTarget, setRefundTarget] = useState(null)

  const load = () => {
    setLoading(true)
    fetchAdminPayments()
      .then(data => { setPayments(data); setError('') })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleRefund = async (paymentId, reason) => {
    const updated = await refundPayment(paymentId, reason)
    setPayments(prev => prev.map(p => p.payment_id === paymentId ? updated : p))
  }

  // 현재 결제 흐름은 승인 시 SUCCESS/FAILED를 즉시 기록하므로 대기 결제는 관리자 UI에 노출하지 않는다.
  const filtered = payments.filter(p =>
    p.status !== 'PENDING' && (filter === 'all' || p.status === filter)
  )

  if (loading) return <div className="loading-text">결제 내역 로딩 중…</div>
  if (error)   return <div className="loading-text" style={{ color:'#c00' }}>{error}</div>

  return (
    <div>
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
        <button className="btn-outline btn-sm" onClick={load}>새로고침</button>
      </div>

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>주문번호</th>
              <th>수단</th>
              <th>금액/상태</th>
              <th>실패/환불사유</th>
              <th>결제시각</th>
              <th>환불시각</th>
              <th>환불</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={7} className="loading-text">결제 내역이 없습니다</td></tr>
            )}
            {filtered.map(p => (
              <tr key={p.payment_id}>
                <td className="order-number">#{p.order_number}</td>
                <td>{p.method}</td>
                <td>
                  <span style={{ marginRight:'8px' }}>{Number(p.amount).toLocaleString('ko-KR')}원</span>
                  <StatusBadge type="payment" value={p.status} />
                </td>
                <td style={{ color: p.failure_reason ? '#c0392b' : '#ccc', fontSize:'13px' }}>
                  {p.failure_reason ?? '–'}
                </td>
                <td style={{ color:'#888', fontSize:'13px' }}>{fmtDatetime(p.paid_at)}</td>
                <td style={{ color:'#888', fontSize:'13px' }}>{p.refunded_at ? fmtDatetime(p.refunded_at) : '–'}</td>
                <td>
                  {p.status === 'SUCCESS' ? (
                    <button className="btn-danger btn-sm" onClick={() => setRefundTarget(p)}>환불</button>
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
