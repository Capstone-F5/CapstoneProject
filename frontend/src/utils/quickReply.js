// 짧은 긍정/부정 응답("네", "그래", "어", "아니요" 등) 판별.
// 전사 결과가 이 사전과 '정확히' 일치할 때만 yes/no로 본다(부분 일치 X) — 문장이 섞이면 LLM이 처리한다.
// 화면이 예/아니오를 기다리는 상태일 때만 쓰이므로, 필러 "어"도 긍정으로 넣는다.
const YES = new Set([
  '네', '넵', '넹', '예', '응', '웅', '어', '그래', '그래요', '그렇지', '좋아', '좋아요',
  '맞아', '맞아요', '맞습니다', '알겠어', '알겠어요', '알겠습니다', '오케이', '콜',
  'yes', 'yeah', 'yep', 'yup', 'ok', 'okay', 'sure',
  'はい', 'うん', '好', '好的', '是', '对',
])

const NO = new Set([
  '아니', '아니요', '아니오', '아뇨', '아냐', '아니야', '싫어', '싫어요', '안해', '안해요',
  'no', 'nope', 'nah',
  'いいえ', 'ううん', '不', '不要', '不是',
])

// 문장부호·공백 제거, 영문은 소문자
function normalize(text) {
  return (text ?? '')
    .toLowerCase()
    .replace(/[\s.,!?~…·'"`。、！？，]+/g, '')
}

/** @returns {'yes' | 'no' | null} */
export function classifyQuickReply(text) {
  const t = normalize(text)
  if (!t) return null
  if (YES.has(t)) return 'yes'
  if (NO.has(t))  return 'no'
  return null
}
