// 이모지(🗑 💳 💵 📷 ✋ 🍔 …) 대신 쓰는 인라인 SVG 아이콘.
//
// 이모지는 글꼴에 의존한다. 키오스크(Pi4B Chromium)에는 컬러 이모지 글꼴이 없어서 외부(Google Fonts)에서 받아 쓰고 있었는데,
// 네트워크가 느리거나 막히면 휴지통·카드 같은 아이콘이 네모(□)로 깨진다(Pi4B 이모티콘 렌더링 수정 후에도 재발).
// SVG는 글꼴·네트워크와 무관하게 항상 같게 그려진다.
//
// 사용: <Glyph ch="🗑" />  — ch는 기존 코드의 이모지 문자 그대로다(메뉴 데이터의 emoji 필드도 그대로 넘기면 된다).
// 크기는 글자 크기(1em)를 따르므로 부모의 fontSize가 그대로 아이콘 크기가 된다. 모르는 문자는 글자 그대로 그린다.

const BROWN = '#744032'
const YELLOW = '#F5B800'

const ICONS = {
  // ── UI 아이콘: 색은 부모의 color(currentColor)를 따른다 ─────────────────────
  trash: (
    <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 7h16" />
      <path d="M9 7V4.5h6V7" />
      <path d="M6 7l1 13h10l1-13" />
      <path d="M10 11v6M14 11v6" />
    </g>
  ),
  card: (
    <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2.5" y="5" width="19" height="14" rx="2.5" />
      <path d="M2.5 9.5h19" />
      <path d="M6 15h4" />
    </g>
  ),
  cash: (
    <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2.5" y="6" width="19" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.7" />
      <path d="M6 9.5v.01M18 14.5v.01" />
    </g>
  ),
  camera: (
    <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3.5 8.5a2 2 0 0 1 2-2h2l1.5-2h6l1.5 2h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z" />
      <circle cx="12" cy="13" r="3.6" />
    </g>
  ),
  info: (
    <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5.5M12 7.8v.01" />
    </g>
  ),
  // 손 모양(제스처 안내): 펼친 손 / 주먹
  palm: (
    <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 12V5.5a1.5 1.5 0 0 1 3 0V11" />
      <path d="M11 11V4a1.5 1.5 0 0 1 3 0v7" />
      <path d="M14 11V5.5a1.5 1.5 0 0 1 3 0V13" />
      <path d="M17 11.5a1.5 1.5 0 0 1 3 0V15a7 7 0 0 1-7 7h-1.2a6 6 0 0 1-4.9-2.5L4 14.8a1.5 1.5 0 0 1 2.3-1.9L8 14.5V12" />
    </g>
  ),
  fist: (
    <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 11V8.5a1.5 1.5 0 0 1 3 0V10" />
      <path d="M10 10V7.5a1.5 1.5 0 0 1 3 0V10" />
      <path d="M13 10V8.5a1.5 1.5 0 0 1 3 0V12" />
      <path d="M16 11.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-2a6 6 0 0 1-6-6v-3.5a1.5 1.5 0 0 1 3 0" />
    </g>
  ),
  // ── 음식·장식: 앱 색상(갈색·노랑) 고정 ─────────────────────────────────────
  burger: (
    <g strokeLinejoin="round" strokeLinecap="round">
      <path d="M3.5 11a8.5 7 0 0 1 17 0z" fill={YELLOW} stroke={BROWN} strokeWidth="1.4" />
      <path d="M3 13.5c2 1.8 3.5-1.2 6 0s3.5 1.8 6 0 3.5-1.2 6 0" fill="none" stroke="#5a9a3a" strokeWidth="1.8" />
      <rect x="3.5" y="15" width="17" height="2.6" rx="1.3" fill={BROWN} />
      <path d="M3.5 18.8h17v.2a2.2 2.2 0 0 1-2.2 2.2H5.7A2.2 2.2 0 0 1 3.5 19z" fill={YELLOW} stroke={BROWN} strokeWidth="1.4" />
    </g>
  ),
  fries: (
    <g strokeLinejoin="round" strokeLinecap="round">
      <path d="M7 4.5v8M10 3v9.5M13 3.5v9M16 4.5v8" stroke={YELLOW} strokeWidth="2.2" fill="none" />
      <path d="M5.5 10.5h13l-1.4 10h-10.2z" fill="#d32f2f" stroke={BROWN} strokeWidth="1.2" />
    </g>
  ),
  cup: (
    <g strokeLinejoin="round" strokeLinecap="round">
      <path d="M13 2.5l1.5 4" stroke={BROWN} strokeWidth="1.6" fill="none" />
      <rect x="5" y="6" width="14" height="2.6" rx="1.3" fill={BROWN} />
      <path d="M6.2 8.6h11.6l-1.2 11.9a1.5 1.5 0 0 1-1.5 1.3H8.9a1.5 1.5 0 0 1-1.5-1.3z" fill="#fff" stroke={BROWN} strokeWidth="1.4" />
      <path d="M6.9 13h10.2l-.6 7H7.5z" fill={YELLOW} />
    </g>
  ),
  bento: (
    <g strokeLinejoin="round" strokeLinecap="round" stroke={BROWN} strokeWidth="1.4">
      <rect x="3" y="5" width="18" height="14" rx="2.5" fill="#fff" />
      <path d="M12 5v14M3 12h9" fill="none" />
      <circle cx="7.5" cy="8.5" r="1.6" fill={YELLOW} stroke="none" />
      <circle cx="16.5" cy="12" r="2.8" fill="#d32f2f" stroke="none" />
      <path d="M5 15.5h5" fill="none" stroke="#5a9a3a" strokeWidth="2" />
    </g>
  ),
  plate: (
    <g fill="none" stroke={BROWN} strokeWidth="1.5" strokeLinecap="round">
      <circle cx="12" cy="12" r="8.5" fill="#fff" />
      <circle cx="12" cy="12" r="5" />
    </g>
  ),
  party: (
    <g strokeLinejoin="round" strokeLinecap="round">
      <path d="M3.5 20.5L8 8l8 8z" fill={YELLOW} stroke={BROWN} strokeWidth="1.4" />
      <path d="M13 5.5v.01M18 9v.01M19.5 4v.01M15.5 11.5v.01" stroke="#d32f2f" strokeWidth="2.4" fill="none" />
      <path d="M11 6c1.5-1 2.5-1 3.5 0" fill="none" stroke={BROWN} strokeWidth="1.3" />
    </g>
  ),
}

// 이모지 문자 → 아이콘 이름 (변형 선택자 U+FE0F는 떼고 찾는다)
const BY_CHAR = {
  '🗑': 'trash', '💳': 'card', '💵': 'cash', '📷': 'camera', 'ℹ': 'info', '✋': 'palm', '✊': 'fist',
  '🍔': 'burger', '🍟': 'fries', '🥤': 'cup', '🍱': 'bento', '🍽': 'plate', '🎉': 'party',
}

export default function Glyph({ ch, size = '1em', style, title }) {
  const name = ICONS[ch] ? ch : BY_CHAR[String(ch ?? '').replace(/️/g, '')]
  if (!name) return <>{ch}</>   // 모르는 문자는 글자 그대로(이모지 글꼴이 있으면 그대로 보인다)
  return (
    <svg
      viewBox="0 0 24 24" width={size} height={size} role={title ? 'img' : 'presentation'} aria-label={title} aria-hidden={title ? undefined : true}
      style={{ display: 'inline-block', verticalAlign: '-0.14em', flexShrink: 0, ...style }}
    >
      {ICONS[name]}
    </svg>
  )
}
