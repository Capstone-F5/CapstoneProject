export default function StatusBadge({ type, value }) {
  const ORDER_MAP = {
    RECEIVED:  { cls: 'badge-received',  label: '접수' },
    COOKING:   { cls: 'badge-cooking',   label: '조리중' },
    READY:     { cls: 'badge-ready',     label: '준비완료' },
    COMPLETED: { cls: 'badge-completed', label: '완료' },
    CANCELLED: { cls: 'badge-cancelled', label: '취소' },
  }
  const PAY_MAP = {
    PENDING:  { cls: 'badge-pending',  label: '대기' },
    SUCCESS:  { cls: 'badge-success',  label: '완료' },
    FAILED:   { cls: 'badge-failed',   label: '실패' },
    REFUNDED: { cls: 'badge-refunded', label: '환불됨' },
  }

  const map = type === 'payment' ? PAY_MAP : ORDER_MAP
  const info = map[value] ?? { cls: 'badge-pending', label: value }

  return <span className={`badge ${info.cls}`}>{info.label}</span>
}
