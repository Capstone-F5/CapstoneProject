import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchAdminOrders, updateOrderNote, updateOrderStatus } from '../api/adminApi.js'
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

const STATUS_LABELS = { COOKING: '조리중', READY: '준비완료', COMPLETED: '완료' }

function StatusAdvanceControl({ status, onChange, compact = false, openUp = false }) {
  const [open, setOpen] = useState(false)
  const index = ORDER_STATUSES.indexOf(status)
  const options = index >= 0 ? ORDER_STATUSES.slice(index + 1) : []
  if (!options.length) return null

  const next = options[0]
  return (
    <div style={{ display:'inline-flex', alignItems:'stretch', verticalAlign:'middle', position:'relative' }}>
      <button
        type="button"
        className={`btn-primary${compact ? ' btn-sm' : ''}`}
        style={{
          borderTopRightRadius: 0,
          borderBottomRightRadius: 0,
          ...(compact ? { padding: '4px 8px' } : { flex: 1, padding: '12px', fontSize: '14px' }),
        }}
        onClick={() => onChange(next)}
      >
        {nextLabel(status)}
      </button>
      <button
        type="button"
        className="btn-primary"
        style={{
          width: compact ? '30px' : '40px',
          padding: 0,
          borderTopLeftRadius: 0,
          borderBottomLeftRadius: 0,
          borderLeft: '1px solid rgba(255,255,255,.45)',
          cursor: 'pointer',
          textAlign: 'center',
        }}
        aria-label="다른 주문 상태 선택"
        aria-expanded={open}
        onClick={() => setOpen(prev => !prev)}
      >
        ▾
      </button>
      {open && (
        <div
          role="menu"
          style={{
            position:'absolute',
            ...(openUp ? { bottom:'calc(100% + 4px)' } : { top:'calc(100% + 4px)' }),
            right:0, zIndex:30,
            minWidth: compact ? '132px' : '160px', padding:'4px',
            border:'1px solid #ddd', borderRadius:'6px', background:'#fff',
            boxShadow:'0 4px 12px rgba(0,0,0,.16)',
          }}
        >
          {options.map(value => (
            <button
              key={value}
              type="button"
              role="menuitem"
              onClick={() => { setOpen(false); onChange(value) }}
              style={{
                display:'block', width:'100%', padding:'8px 10px', border:0,
                borderRadius:'4px', background:'transparent', color:'#333',
                textAlign:'left', fontSize:'12px', cursor:'pointer', whiteSpace:'nowrap',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#f5f5f5' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
            >
              {STATUS_LABELS[value]}로 변경
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function OrderNoteInput({ order, onSave }) {
  const [note, setNote] = useState(order.admin_note ?? '')
  const [saving, setSaving] = useState(false)

  useEffect(() => setNote(order.admin_note ?? ''), [order.order_id, order.admin_note])

  const save = async () => {
    if (saving) return
    setSaving(true)
    try {
      await onSave(order.order_id, note)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display:'flex', alignItems:'center', gap:'4px', minWidth:0 }}>
      <input
        value={note}
        maxLength={500}
        placeholder="비고 입력"
        onChange={e => setNote(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') save() }}
        style={{ minWidth:0, width:'100%', padding:'5px 7px', border:'1px solid #ddd', borderRadius:'4px', fontSize:'12px' }}
        aria-label={`주문 ${order.order_number} 비고`}
      />
      <button type="button" className="chip" disabled={saving} onClick={save} style={{ padding:'4px 7px', fontSize:'11px', whiteSpace:'nowrap' }}>
        {saving ? '…' : '저장'}
      </button>
    </div>
  )
}

function nextLabel(status) {
  return {
    RECEIVED: '\uC870\uB9AC\uC911\uC73C\uB85C \uBCC0\uACBD',
    COOKING: '\uC900\uBE44\uC644\uB8CC\uB85C \uBCC0\uACBD',
    READY: '\uC644\uB8CC\uB85C \uBCC0\uACBD',
  }[status]
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

const ELAPSED_ACTIVE = new Set(['RECEIVED', 'COOKING'])

function elapsedColor(minutes) {
  if (minutes <= 7)  return { bg: '#e8f5e9', color: '#2e7d32' }  // 연두
  if (minutes <= 15) return { bg: '#fff8e1', color: '#f57f17' }  // 노랑
  if (minutes <= 25) return { bg: '#fff3e0', color: '#e65100' }  // 주황
  return               { bg: '#fde8e8', color: '#c0392b' }       // 빨강
}

function ElapsedBadge({ createdAt, now }) {
  const minutes = Math.floor((now - new Date(createdAt)) / 60000)
  const { bg, color } = elapsedColor(minutes)
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 999,
      fontSize: 12, fontWeight: 700, background: bg, color,
      whiteSpace: 'nowrap',
    }}>
      {minutes}분
    </span>
  )
}

function optionLabels(options) {
  if (!Array.isArray(options)) {
    if (typeof options !== 'string') return []
    try {
      const parsed = JSON.parse(options)
      options = Array.isArray(parsed) ? parsed : [options]
    } catch {
      options = [options]
    }
  }

  return options.map(option => {
    if (typeof option === 'string' || typeof option === 'number') return String(option)
    if (option && typeof option === 'object') {
      return String(option.name_ko ?? option.name ?? option.label ?? option.option_id ?? '')
    }
    return ''
  }).filter(Boolean)
}

function OrderDetail({ order, onClose, onStatusChange }) {
  if (!order) return null
  const next = nextStatus(order.status)
  const items = Array.isArray(order.items) ? order.items : []

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
        {items.map((item, i) => {
          const options = optionLabels(item.selected_options)
          return (
          <div key={i}>
            <div style={{ display:'flex', justifyContent:'space-between', fontWeight:'500', marginBottom:'4px' }}>
              <span>{item.name_ko} X{item.quantity}</span>
              <span>{Number(item.total_price).toLocaleString('ko-KR')}원</span>
            </div>
            {options.length > 0 && (
              <div style={{ fontSize:'12px', color:'#888', paddingLeft:'8px', lineHeight:'1.8' }}>
                {options.map((option, j) => <div key={j}>{option}</div>)}
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
          )
        })}
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
          <div style={{ display:'flex', width:'100%' }}>
            <StatusAdvanceControl
              status={order.status}
              onChange={status => onStatusChange(order.order_id, status)}
              openUp
            />
          </div>
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
  const [now,         setNow]         = useState(new Date())
  const timerRef = useRef(null)
  const clockRef = useRef(null)

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
    timerRef.current = setInterval(load, 10000)
    clockRef.current = setInterval(() => setNow(new Date()), 15000)
    return () => { clearInterval(timerRef.current); clearInterval(clockRef.current) }
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

  const handleNoteSave = async (orderId, adminNote) => {
    try {
      const updated = await updateOrderNote(orderId, adminNote)
      setOrders(prev => prev.map(o => o.order_id === orderId ? updated : o))
      setSelected(prev => prev?.order_id === orderId ? updated : prev)
    } catch (e) {
      alert(`비고 저장 실패: ${e.message}`)
    }
  }

  const handleSelectOrder = (order) => {
    if (selected?.order_id === order.order_id) {
      setSelected(null)
      return
    }
    // 목록 응답에 영수증에 필요한 주문·품목 정보가 이미 포함되어 있다.
    // 클릭 즉시 표시해 상세 API 오류가 패널 렌더링을 막지 않도록 한다.
    setSelected(order)
  }

  const filtered = orders.filter(o => {
    if (filter === 'all')        return true
    if (filter === 'incomplete') return ['RECEIVED','COOKING','READY'].includes(o.status)
    return o.status === filter
  })

  const selectedOrder = selected

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
            10초 자동 갱신 · 마지막 갱신 {lastRefresh.getHours().toString().padStart(2,'0')}:{lastRefresh.getMinutes().toString().padStart(2,'0')}:{lastRefresh.getSeconds().toString().padStart(2,'0')}
          </span>
          <button className="btn-outline btn-sm" onClick={load}>새로고침</button>
        </div>
      </div>

      <div style={{ display:'flex', alignItems:'flex-start' }}>
        <div className="card" style={{ flex:1, minWidth:0, padding:'0', overflow:'visible' }}>
          <table className="data-table" style={{ tableLayout:'fixed', width:'100%' }}>
            <colgroup>
              <col style={{ width: 90 }} />
              <col style={{ width: 60 }} />
              <col style={{ width: 100 }} />
              <col style={{ width: 72 }} />
              <col style={{ width: 88 }} />
              <col />
              <col style={{ width: 210 }} />
              <col style={{ width: 170 }} />
            </colgroup>
            <thead>
              <tr>
                <th>주문번호</th>
                <th>유형</th>
                <th>상태</th>
                <th>경과</th>
                <th>결제</th>
                <th>금액(시각)</th>
                <th>상태변경</th>
                <th>비고</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={8} className="loading-text">주문이 없습니다</td></tr>
              )}
              {filtered.map(order => {
                const next = nextStatus(order.status)
                const isSelected = selectedOrder?.order_id === order.order_id
                return (
                  <tr
                    key={order.order_id}
                    className={isSelected ? 'selected' : ''}
                    style={{ cursor:'pointer' }}
                    onClick={() => handleSelectOrder(order)}
                  >
                    <td className="order-number">#{order.order_number}</td>
                    <td>{order.order_type === 'EAT_IN' ? '매장' : '포장'}</td>
                    <td><StatusBadge value={order.status} /></td>
                    <td>
                      {ELAPSED_ACTIVE.has(order.status) && order.created_at
                        ? <ElapsedBadge createdAt={order.created_at} now={now} />
                        : <span style={{ color: '#ccc', fontSize: 12 }}>–</span>
                      }
                    </td>
                    <td>
                      {order.payment_status
                        ? <StatusBadge type="payment" value={order.payment_status} />
                        : <span style={{ color:'#ccc', fontSize:12 }}>–</span>}
                    </td>
                    <td>
                      <span style={{ fontWeight:'500' }}>{Number(order.final_amount).toLocaleString('ko-KR')}원</span>
                      <span style={{ color:'#bbb', marginLeft:'6px', fontSize:'12px' }}>{fmt(order.created_at)}</span>
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      {next && order.status !== 'CANCELLED' ? (
                        <div style={{ display:'flex', gap:'4px', alignItems:'center', flexWrap:'nowrap', whiteSpace:'nowrap' }}>
                          <StatusAdvanceControl
                            status={order.status}
                            onChange={status => handleStatusChange(order.order_id, status)}
                            compact
                          />
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
                    <td onClick={e => e.stopPropagation()}>
                      <OrderNoteInput order={order} onSave={handleNoteSave} />
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
