import { useState } from 'react'
import { DUMMY_STATS } from '../api/adminApi.js'

function fmt(n) {
  return n.toLocaleString('ko-KR')
}

function BarChart({ data }) {
  const max = Math.max(...data.map(d => d.sales), 1)
  const CHART_H = 160

  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: CHART_H + 28, padding: '0 4px' }}>
      {data.map((d, i) => {
        const barH = Math.round((d.sales / max) * CHART_H)
        const isLast = i === data.length - 1
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
            <div
              title={`${d.date}: ${fmt(d.sales)}원`}
              style={{
                width: '100%',
                height: barH,
                background: isLast ? '#744032' : '#F5B800',
                borderRadius: '4px 4px 0 0',
                transition: 'height 0.3s',
              }}
            />
            <span style={{ fontSize: '11px', color: '#999', whiteSpace: 'nowrap' }}>{d.date}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function DashboardPage() {
  const [range, setRange] = useState('7d')
  const stats = DUMMY_STATS
  const salesData = range === '7d' ? stats.sales_7d : stats.sales_30d

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Period toggle */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <div style={{ display: 'flex', borderRadius: '8px', overflow: 'hidden', border: '1.5px solid #ddd' }}>
          {['7d', '30d'].map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              style={{
                padding: '6px 20px',
                fontSize: '13px',
                fontWeight: '600',
                border: 'none',
                background: range === r ? '#744032' : '#fff',
                color: range === r ? '#fff' : '#555',
                cursor: 'pointer',
                fontFamily: 'Pretendard, sans-serif',
              }}
            >
              {r === '7d' ? '7일' : '30일'}
            </button>
          ))}
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {[
          { label: '오늘 매출 합계', value: `${fmt(stats.summary.today_sales)}원`, color: '#744032' },
          { label: '오늘 주문 건수', value: `${fmt(stats.summary.order_count)}건`, color: '#744032' },
          { label: '평균 객단가',    value: `${fmt(stats.summary.avg_order_value)}원`, color: '#744032' },
        ].map(card => (
          <div key={card.label} className="card">
            <div style={{ fontSize: '13px', color: '#999', marginBottom: '10px' }}>{card.label}</div>
            <div style={{ fontSize: '26px', fontWeight: '700', color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Sales chart */}
      <div className="card">
        <div style={{ fontWeight: '600', fontSize: '15px', marginBottom: '20px' }}>
          최근 {range === '7d' ? '7일' : '30일'} 매출 추이
        </div>
        <BarChart data={salesData} />
      </div>

      {/* Popular items */}
      <div className="card">
        <div style={{ fontWeight: '600', fontSize: '15px', marginBottom: '16px' }}>인기 메뉴 랭킹</div>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 48 }}>순위</th>
              <th>메뉴명</th>
              <th style={{ textAlign: 'right' }}>판매수량</th>
              <th style={{ textAlign: 'right' }}>매출</th>
            </tr>
          </thead>
          <tbody>
            {stats.popular_items.map((item, i) => (
              <tr key={item.menu_item_id}>
                <td style={{ color: i < 3 ? '#744032' : '#999', fontWeight: i < 3 ? '700' : '400' }}>
                  {i + 1}
                </td>
                <td style={{ fontWeight: '500' }}>{item.name_ko}</td>
                <td style={{ textAlign: 'right' }}>{fmt(item.quantity_sold)}개</td>
                <td style={{ textAlign: 'right', fontWeight: '600' }}>{fmt(item.revenue)}원</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
