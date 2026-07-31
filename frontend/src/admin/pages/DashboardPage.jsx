import { useState, useEffect } from 'react'
import { fetchStatsSummary, fetchSalesSeries, fetchPopularItems, fetchCategorySales, fetchPaymentMethodStats } from '../api/adminApi.js'

function fmt(n) {
  return Math.round(n).toLocaleString('ko-KR')
}

function shortDate(dateStr) {
  // "YYYY-MM-DD" → "M/D"
  const [, m, d] = (dateStr ?? '').split('-')
  return m && d ? `${parseInt(m)}/${parseInt(d)}` : dateStr
}

function CategorySalesChart({ data }) {
  const max = Math.max(...data.map(d => d.revenue), 1)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {data.map(item => (
        <div key={item.category_id}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 5 }}>
            <span style={{ fontWeight: 500 }}>{item.name_ko}</span>
            <span style={{ color: '#744032', fontWeight: 600 }}>
              {item.ratio}% &nbsp;·&nbsp; {fmt(item.revenue)}원
            </span>
          </div>
          <div style={{ background: '#f5f5f5', borderRadius: 4, height: 8 }}>
            <div style={{
              width: `${(item.revenue / max) * 100}%`,
              background: '#744032', borderRadius: 4, height: '100%',
              transition: 'width 0.4s',
            }} />
          </div>
        </div>
      ))}
    </div>
  )
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
              title={`${shortDate(d.date)}: ${fmt(d.sales)}원`}
              style={{
                width: '100%',
                height: barH,
                background: isLast ? '#744032' : '#F5B800',
                borderRadius: '4px 4px 0 0',
                transition: 'height 0.3s',
              }}
            />
            <span style={{ fontSize: '11px', color: '#999', whiteSpace: 'nowrap' }}>{shortDate(d.date)}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function DashboardPage() {
  const [range, setRange]               = useState('7d')
  const [summary, setSummary]           = useState(null)
  const [salesData, setSalesData]       = useState([])
  const [popular, setPopular]           = useState([])
  const [categorySales, setCategorySales] = useState([])
  const [paymentStats, setPaymentStats] = useState([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    Promise.all([
      fetchStatsSummary(),
      fetchSalesSeries(range),
      fetchPopularItems(range),
      fetchCategorySales(range),
      fetchPaymentMethodStats(range),
    ])
      .then(([sum, sales, pop, cats, pmts]) => {
        setSummary(sum)
        setSalesData(sales.data ?? [])
        setPopular(pop)
        setCategorySales(cats)
        setPaymentStats(pmts)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [range])

  if (loading) return <div className="loading-text">통계 로딩 중…</div>
  if (error)   return <div className="loading-text" style={{ color:'#c00' }}>{error}</div>

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
                padding: '6px 20px', fontSize: '13px', fontWeight: '600',
                border: 'none', cursor: 'pointer', fontFamily: 'Pretendard, sans-serif',
                background: range === r ? '#744032' : '#fff',
                color:      range === r ? '#fff'    : '#555',
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
          { label: '오늘 매출 합계', value: `${fmt(summary?.today_sales ?? 0)}원` },
          { label: '오늘 주문 건수', value: `${fmt(summary?.order_count ?? 0)}건` },
          { label: '평균 객단가',    value: `${fmt(summary?.avg_order_value ?? 0)}원` },
        ].map(card => (
          <div key={card.label} className="card">
            <div style={{ fontSize: '13px', color: '#999', marginBottom: '10px' }}>{card.label}</div>
            <div style={{ fontSize: '26px', fontWeight: '700', color: '#744032' }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Sales chart */}
      <div className="card">
        <div style={{ fontWeight: '600', fontSize: '15px', marginBottom: '20px' }}>
          최근 {range === '7d' ? '7일' : '30일'} 매출 추이
        </div>
        {salesData.length > 0
          ? <BarChart data={salesData} />
          : <div className="loading-text">데이터가 없습니다</div>
        }
      </div>

      {/* Popular items */}
      <div className="card">
        <div style={{ fontWeight: '600', fontSize: '15px', marginBottom: '16px' }}>인기 메뉴 랭킹</div>
        {popular.length === 0
          ? <div className="loading-text">데이터가 없습니다</div>
          : (
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
                {popular.map((item, i) => (
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
          )
        }
      </div>

      {/* Category sales */}
      <div className="card">
        <div style={{ fontWeight: '600', fontSize: '15px', marginBottom: '16px' }}>카테고리별 매출 비율</div>
        {categorySales.length === 0
          ? <div className="loading-text">데이터가 없습니다</div>
          : <CategorySalesChart data={categorySales} />
        }
      </div>

      {/* Payment method stats */}
      <div className="card">
        <div style={{ fontWeight: '600', fontSize: '15px', marginBottom: '16px' }}>결제수단별 집계</div>
        {paymentStats.length === 0
          ? <div className="loading-text">데이터가 없습니다</div>
          : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>결제수단</th>
                  <th style={{ textAlign: 'right' }}>건수</th>
                  <th style={{ textAlign: 'right' }}>합계</th>
                </tr>
              </thead>
              <tbody>
                {paymentStats.map(p => (
                  <tr key={p.method}>
                    <td style={{ fontWeight: 500 }}>{p.method}</td>
                    <td style={{ textAlign: 'right' }}>{fmt(p.count)}건</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{fmt(p.total_amount)}원</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </div>
    </div>
  )
}
