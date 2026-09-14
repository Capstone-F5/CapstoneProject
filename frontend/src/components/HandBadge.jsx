import { useGestureUIEnabled } from '../contexts/GestureUIContext'

const VARIANT_CONFIG = {
  primary: { bg: '#744032', color: 'y', cardRadius: 16 }, // 갈색 배경 + 노란 손 (매장/포장/단품세트 카드용, 카드 모서리 16px)
  option:  { bg: '#F5B800', color: 'b', cardRadius: 10 }, // 노란 배경 + 갈색 손 (사이드/음료 옵션 칩용, 카드 모서리 10px)
}

/**
 * hand{number}_{b|y}.webp 이미지를 카드 왼쪽 위 모서리에 "리본"처럼 밀착시켜 붙이는 컴포넌트.
 * 이미지는 frontend/public/images/hand/ 에 위치해야 함.
 *
 * - 카드 밖으로 튀어나오지 않고 카드 내부에 완전히 들어감 (top:0, left:0 고정).
 * - 왼쪽 위 모서리는 카드 자체의 둥근 정도(cardRadius)와 똑같이 맞춰서 카드 모서리에
 *   꽉 차게 파묻힌 것처럼 보이고, 오른쪽 아래(안쪽) 모서리는 할인 리본처럼 살짝만
 *   둥글게 처리해서 뭉툭해 보이지 않게 함.
 *
 * variant="primary" (기본) — 갈색 배경 + 노란 손, 44px. 매장/포장/단품·세트 카드용.
 * variant="option"          — 노란 배경 + 갈색 손, 22px. 제외하기/사이드/음료 옵션 칩용.
 */
export default function HandBadge({ number, variant = 'primary', size, cardRadius }) {
  const gestureEnabled = useGestureUIEnabled()
  if (!number || !gestureEnabled) return null

  const config = VARIANT_CONFIG[variant] ?? VARIANT_CONFIG.primary
  const badgeSize = size ?? (variant === 'option' ? 22 : 44)
  const radius = cardRadius ?? config.cardRadius

  // 왼쪽 위: 카드 모서리와 완전히 동일한 반경 (꽉 채움)
  // 오른쪽 아래: 살짝만 둥글게 (할인 리본 정도의 은은한 굴곡)
  const innerCorner = Math.max(6, badgeSize * 0.22)
  const borderRadius = `${radius}px 0 ${innerCorner}px 0`

  const isCombo = number > 5
  const n = Math.min(Math.max(number, 1), 5)

  const boxStyle = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: badgeSize,
    height: badgeSize,
    borderRadius,
    background: config.bg,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
    pointerEvents: 'none',
    overflow: 'hidden',
  }

  if (isCombo) {
    // 6 이상은 "5개 편 손 + 나머지 개수"를 배지 안에 나란히 배치 (카드 밖으로 안 나가게 폭 안에서 축소)
    const rest = Math.min(number - 5, 5)
    return (
      <div style={boxStyle}>
        <img
          src={`/images/hand/hand5_${config.color}.webp`}
          alt="손동작 5"
          style={{ width: '46%', height: '70%', objectFit: 'contain', flexShrink: 0 }}
        />
        <img
          src={`/images/hand/hand${rest}_${config.color}.webp`}
          alt={`손동작 ${rest}`}
          style={{ width: '38%', height: '70%', objectFit: 'contain', flexShrink: 0 }}
        />
      </div>
    )
  }

  return (
    <div style={boxStyle}>
      <img
        src={`/images/hand/hand${n}_${config.color}.webp`}
        alt={`손동작 ${n}`}
        style={{ width: '68%', height: '68%', objectFit: 'contain' }}
      />
    </div>
  )
}
