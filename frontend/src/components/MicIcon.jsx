// 마이크 픽토그램(선형 SVG) — 이모지 대신 쓴다. 색은 부모의 color(currentColor)를 따른다.
// kind="spinner"면 인식 중 표시용 회전 아이콘. 회전 키프레임은 사용하는 쪽에서 `micSpin`으로 정의한다.
export default function MicIcon({ size = 28, kind = 'mic' }) {
  const common = {
    width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
    stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round',
    'aria-hidden': true, focusable: 'false',
  }
  if (kind === 'spinner') {
    return (
      <svg {...common} style={{ animation: 'micSpin .9s linear infinite' }}>
        <path d="M12 3a9 9 0 1 0 9 9" />
      </svg>
    )
  }
  return (
    <svg {...common}>
      <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0" />
      <path d="M12 17.5V21" />
      <path d="M8.5 21h7" />
    </svg>
  )
}
