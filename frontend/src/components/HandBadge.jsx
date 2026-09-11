const VARIANT_CONFIG = {
  primary: { bg: '#744032', color: 'y' }, // 갈색 배경 + 노란 손 이미지 (매장/포장 카드용)
  option:  { bg: '#F5B800', color: 'b' }, // 노란 배경 + 갈색 손 이미지 (사이드/음료 옵션용)
}

/**
 * hand{number}_{b|y}.webp 이미지를 카드/버튼 모서리에 배지로 붙이는 컴포넌트.
 * 이미지는 frontend/public/images/hand/ 에 위치해야 함.
 *
 * variant="primary" (기본) — 갈색 배경 + 노란 손 이미지, 44px. 매장/포장 같은 큰 선택 카드용.
 * variant="option"          — 노란 배경 + 갈색 손 이미지, 22px. 제외하기/사이드/음료 같은 작은 옵션 버튼용.
 *
 * number=6이면 손가락 5개 편 손 + 손가락 1개를 나란히 배치해서 6을 표현함.
 * (이 경우 배지 너비를 늘려서 두 이미지가 겹치지 않도록 함)
 */
export default function HandBadge({ number, variant = 'primary', size, offset }) {
  if (!number) return null
  const config = VARIANT_CONFIG[variant] ?? VARIANT_CONFIG.primary
  const badgeSize = size ?? (variant === 'option' ? 22 : 44)
  const pos = offset ?? (variant === 'option' ? 2 : -14)

  if (number > 5) {
    const boxWidth = badgeSize * 1.55 // 두 손 이미지가 들어갈 만큼 가로로 넓힘
    return (
      <div
        style={{
          position: 'absolute',
          top: pos,
          left: pos,
          width: boxWidth,
          height: badgeSize,
          borderRadius: badgeSize * 0.32,
          background: config.bg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10,
          pointerEvents: 'none',
          overflow: 'hidden',
        }}
      >
        <img
          src={`/images/hand/hand5_${config.color}.webp`}
          alt="손동작 5"
          style={{ height: '74%', width: 'auto', objectFit: 'contain', flexShrink: 0 }}
        />
        <img
          src={`/images/hand/hand${Math.min(number - 5, 5)}_${config.color}.webp`}
          alt={`손동작 ${number - 5}`}
          style={{ height: '74%', width: 'auto', objectFit: 'contain', flexShrink: 0, marginLeft: 2 }}
        />
      </div>
    )
  }

  const n = Math.min(Math.max(number, 1), 5)

  return (
    <div
      style={{
        position: 'absolute',
        top: pos,
        left: pos,
        width: badgeSize,
        height: badgeSize,
        borderRadius: badgeSize * 0.32,
        background: config.bg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      <img
        src={`/images/hand/hand${n}_${config.color}.webp`}
        alt={`손동작 ${n}`}
        style={{ width: '76%', height: '76%', objectFit: 'contain' }}
      />
    </div>
  )
}
