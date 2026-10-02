// 주문번호는 order_number UNIQUE 제약이 날짜별 번호 초기화와 충돌하지 않도록
// DB에 YYYYMMDDNNN(11자리)으로 저장된다. 화면에는 고객이 실제로 받는 번호(뒤 3자리)만
// 보여주고 전체 값은 title로 남긴다. 형식 도입 전 주문은 '34' 같은 일련번호라 그대로 둔다.
export function formatOrderNumber(value) {
  const s = String(value ?? '')
  return /^\d{11}$/.test(s) ? s.slice(-3) : s
}

export default function OrderNumber({ value, style }) {
  const full = String(value ?? '')
  return (
    <span className="order-number" style={style} title={full}>
      #{formatOrderNumber(value)}
    </span>
  )
}
