import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchAdminOrders, updateOrderStatus } from '../api/adminApi.js'
import StatusBadge from '../components/StatusBadge.jsx'

const STATUS_FILTERS = [
  { key: 'incomplete', label: '미완료' },
  { key: 'all',        label: '전체' },
  { key: 'RECEIVED',   label: '접수' },
  { key: 'COOKING',    label: '조리중' },
  { key: 'READY',      label: '준비완료' },
  { key: 'COMPLETED',  label: '완료됨' },
  { key: 'CANCELLED',  label: '취소됨' },
]

const ORDER_STATUSES = ['RECEIVED', 'COOKING', 'READY', 'COMPLETED']

function nextStatus(current) {
  const idx = ORDER_STATUSES.indexOf(current)
  return idx >= 0 && idx < ORDER_STATUSES.length - 1 ? ORDER_STATUSES[idx + 1] : null
}

function nextLabel(status) {
  return { RECEIVED: '조리중으로', COOKING: '준비완료로', READY: '완료로' }[status]
}

function fmt(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

function fmtFull(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

function OrderDetail({ order, onClose, onStatusChange }) {
  if (!order) return null
  const next = nextStatus(order.status)

  return (
    <div className="detail-panel" style={{ marginLeft: '16px' }}>
      <button className="detail-panel-close" onClick={onClose}>×</button>
      <div style={{ display:'flex', alignItems:'center', gap:'10px', marginBottom:'16px' }}>
        <span className="order-number" style={{ fontSize:'16px' }}>#{order.order_number}</span>
        <StatusBadge value={order.status} />
      </div>
      <div style={{ fontSize:'13px', color:'#999', marginBottom:'20px' }}>
        {order.order_type === 'EAT_IN'
          ? `매장 · ${order.table_number != null ? order.table_number+'번 테이블' : '테이블 미지정'}`
          : '포장'}
        &nbsp;·&nbsp;{fmtFull(order.created_at)}
      </div>

      <div style={{ fontWeight:'700', fontSize:'14px', marginBottom:'12px' }}>주문 항목</div>
      <div style={{ display:'flex', flexDirection:'column', gap:'14px', marginBottom:'20px' }}>
        {order.items.map((item, i) => (
          <div key={i}>
            <div style={{ display:'flex', justifyContent:'space-between', fontWeight:'500', marginBottom:'4px' }}>
              <span>{item.name_ko} X{item.quantity}</span>
              <span>{Number(item.total_price).toLocaleString('ko-KR')}원</span>
            </div>
            {item.selected_options?.length > 0 && (
              <div style={{ fontSize:'12px', color:'#888', paddingLeft:'8px', lineHeight:'1.8' }}>
                {item.selected_options.map((o,j) => <div key={j}>{o}</div>)}
              </div>
            )}
            {item.special_note && (
              <div style={{ marginTop:'4px' }}>
                <span style={{
                  display:'inline-block', fontSize:'11px', padding:'2px 8px',
                  background:'#fff3e0', color:'#b87800', borderRadius:'4px', fontWeight:'600'
                }}>{item.special_note}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="divider" />
      <div style={{ fontWeight:'700', fontSize:'14px', marginBottom:'12px' }}>결제 정보</div>
      <div style={{ display:'flex', flexDirection:'column', gap:'8px', fontSize:'14px' }}>
        <div style={{ display:'flex', justifyContent:'space-between' }}>
          <span style={{ color:'#888' }}>주문 금액</span>
          <span>{Number(order.subtotal).toLocaleString('ko-KR')}원</span>
        </div>
        {Number(order.discount_amount) > 0 && (
          <div style={{ display:'flex', justifyContent:'space-between' }}>
            <span style={{ color:'#888' }}>할인</span>
            <span style={{ color:'#e00' }}>-{Number(order.discount_amount).toLocaleString('ko-KR')}원</span>
          </div>
        )}
        {Number(order.points_used) > 0 && (
          <div style={{ display:'flex', justifyContent:'space-between' }}>
            <span style={{ color:'#888' }}>포인트 사용</span>
            <span style={{ color:'#e00' }}>-{Number(order.points_used).toLocaleString('ko-KR')}P</span>
          </div>
        )}
        <div className="divider" style={{ margin:'4px 0' }} />
        <div style={{ display:'flex', justifyContent:'space-between', fontWeight:'700', fontSize:'15px' }}>
          <span>결제금액</span>
          <span>{Number(order.final_amount).toLocaleString('ko-KR')}원</span>
        </div>
      </div>

      {next && order.status !== 'CANCELLED' && (
        <div style={{ marginTop:'20px' }}>
          <button
            className="btn-primary"
            style={{ width:'100%', padding:'12px', fontSize:'14px' }}
            onClick={() => onStatusChange(order.order_id, next)}
          >
            {nextLabel(order.status)}으로 변경
          </button>
        </div>
      )}
    </div>
  )
}

export default function OrdersPage() {
  const [orders,      setOrders]      = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState('')
  const [filter,      setFilter]      = useState('incomplete')
  const [selected,    setSelected]    = useState(null)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const timerRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const data = await fetchAdminOrders()
      setOrders(data)
      setLastRefresh(new Date())
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    timerRef.current = setInterval(load, 30000)
    return () => clearInterval(timerRef.current)
  }, [load])

  const handleStatusChange = async (orderId, newStatus) => {
    try {
      const updated = await updateOrderStatus(orderId, newStatus)
      setOrders(prev => prev.map(o => o.order_id === orderId ? updated : o))
      setSelected(prev => prev?.order_id === orderId ? updated : prev)
    } catch (e) {
      alert(`상태 변경 실패: ${e.message}`)
    }
  }

  const filtered = orders.filter(o => {
    if (filter === 'all')        return true
    if (filter === 'incomplete') return ['RECEIVED','COOKING','READY'].includes(o.status)
    return o.status === filter
  })

  const selectedOrder = selected ? orders.find(o => o.order_id === selected.order_id) ?? null : null

  if (loading) return <div className="loading-text">주문 로딩 중…</div>
  if (error)   return <div className="loading-text" style={{ color:'#c00' }}>{error}</div>

  return (
    <div>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'16px' }}>
        <div className="filter-chips">
          {STATUS_FILTERS.map(f => (
            <button
              key={f.key}
              className={`chip${filter === f.key ? ' active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
          <span style={{ fontSize:'12px', color:'#aaa', whiteSpace:'nowrap' }}>
            마지막 갱신 {lastRefresh.getHours().toString().padStart(2,'0')}:{lastRefresh.getMinutes().toString().padStart(2,'0')}:{lastRefresh.getSeconds().toString().padStart(2,'0')}
          </span>
          <button className="btn-outline btn-sm" onClick={load}>새로고침</button>
        </div>
      </div>

      <div style={{ display:'flex', alignItems:'flex-start' }}>
        <div className="card" style={{ flex:1, padding:'0', overflow:'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>주문번호</th>
                <th>유형</th>
                <th>상태</th>
                <th>결제</th>
                <th>금액(시각)</th>
                <th>상태변경</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="loading-text">주문이 없습니다</td></tr>
              )}
              {filtered.map(order => {
                const next = nextStatus(order.status)
                const isSelected = selectedOrder?.order_id === order.order_id
                return (
                  <tr
                    key={order.order_id}
                    className={isSelected ? 'selected' : ''}
                    style={{ cursor:'pointer' }}
                    onClick={() => setSelected(isSelected ? null : order)}
                  >
                    <td className="order-number">#{order.order_number}</td>
                    <td>{order.order_type === 'EAT_IN' ? '매장' : '포장'}</td>
                    <td><StatusBadge value={order.status} /></td>
                    <td><StatusBadge type="payment" value={order.payment_status ?? 'PENDING'} /></td>
                    <td>
                      <span style={{ fontWeight:'500' }}>{Number(order.final_amount).toLocaleString('ko-KR')}원</span>
                      <span style={{ color:'#bbb', marginLeft:'6px', fontSize:'12px' }}>{fmt(order.created_at)}</span>
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      {next && order.status !== 'CANCELLED' ? (
                        <div style={{ display:'flex', gap:'6px', alignItems:'center' }}>
                          <button
                            className="btn-primary btn-sm"
                            onClick={() => handleStatusChange(order.order_id, next)}
                          >
                            {nextLabel(order.status)} →
                          </button>
                          <button
                            className="chip"
                            style={{ padding:'3px 10px', fontSize:'11px' }}
                            onClick={() => { if (confirm('주문을 취소하시겠습니까?')) handleStatusChange(order.order_id, 'CANCELLED') }}
                          >
                            취소
                          </button>
                        </div>
                      ) : (
                        <span className="btn-disabled btn-sm">
                          {order.status === 'COMPLETED' ? '완료됨' : '취소됨'}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {selectedOrder && (
          <OrderDetail
            order={selectedOrder}
            onClose={() => setSelected(null)}
            onStatusChange={handleStatusChange}
          />
        )}
      </div>
    </div>
  )
}
