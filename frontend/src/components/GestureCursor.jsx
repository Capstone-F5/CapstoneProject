/**
 * 손 커서 오버레이 — 화면 위에 포인팅 커서와 드웰 진행률 링을 표시합니다.
 * cursor: [normX, normY] (0~1) 또는 null
 * progress: 드웰 진행률 0~1
 */
export default function GestureCursor({ cursor, progress }) {
  if (!cursor) return null

  const x = cursor[0] * window.innerWidth
  const y = cursor[1] * window.innerHeight
  const r = 22
  const circumference = 2 * Math.PI * r

  return (
    <div
      style={{
        position: 'fixed',
        left: x - 30,
        top: y - 30,
        width: 60,
        height: 60,
        pointerEvents: 'none',
        zIndex: 9999,
        transition: 'left 0.05s linear, top 0.05s linear',
      }}
    >
      <svg width="60" height="60" overflow="visible">
        {/* 외곽 원 */}
        <circle cx="30" cy="30" r={r}
          fill="none" stroke="rgba(0,100,220,0.35)" strokeWidth="2" />
        {/* 중심 점 */}
        <circle cx="30" cy="30" r="5"
          fill="rgba(0,100,220,0.85)" />
        {/* 드웰 진행률 호 */}
        {progress > 0 && (
          <circle cx="30" cy="30" r={r}
            fill="none"
            stroke="rgba(0,210,100,0.9)"
            strokeWidth="3.5"
            strokeDasharray={`${circumference * progress} ${circumference}`}
            strokeLinecap="round"
            transform="rotate(-90 30 30)"
          />
        )}
      </svg>
    </div>
  )
}
