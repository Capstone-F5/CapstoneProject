// TTS 로컬 캐시 — 자주 반복되는 고정 문구를 /audio/common/ 에 사전 저장해 두고
// OpenAI TTS API 호출 없이 즉시 재생한다. 라즈베리파이4 환경에서 API 왕복 지연(~300–800ms)을 제거.
//
// 사전 녹음 파일 생성:
//   cd scripts && node generateCommonAudio.js
// (파일이 없으면 자동으로 API 경로로 fallback 되어 기존 동작 유지)

const AUDIO_BASE = '/audio/common/'

// 정규화 키: 이모지·특수문자 제거, 공백 압축, 소문자화
const normalize = (text) =>
  text.replace(/[\u{1F000}-\u{1FFFF}]/gu, '')
      .replace(/[^\w가-힣\s]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase()

// 자주 등장하는 고정 문구 → 사전 녹음 파일명
// 키: normalize() 적용 결과, 값: AUDIO_BASE 기준 파일명
export const COMMON_PHRASES = {
  '장바구니에 담았습니다':                   'cart_added.mp3',
  '주문이 완료되었습니다':                   'order_complete.mp3',
  '결제가 완료되었습니다':                   'payment_complete.mp3',
  '네 알겠습니다':                           'yes_understood.mp3',
  '죄송합니다 잘 이해하지 못했습니다':       'sorry_not_understood.mp3',
  '다른 도움이 필요하신가요':                'anything_else.mp3',
  '메뉴를 선택해 주세요':                   'select_menu.mp3',
  '수량을 말씀해 주세요':                   'say_quantity.mp3',
}

// 런타임 캐시 — URL을 한 번 생성하면 재사용 (탭 닫힐 때까지 유지)
const _urlCache = new Map()

/**
 * 텍스트가 사전 녹음 파일과 매칭되면 해당 Audio 객체를 반환한다.
 * 매칭 실패 시 null 반환 → 호출자가 API 경로로 fallback.
 */
export async function getCachedAudio(text) {
  const key = normalize(text)
  const filename = COMMON_PHRASES[key]
  if (!filename) return null

  if (_urlCache.has(filename)) {
    const audio = new Audio(_urlCache.get(filename))
    return audio
  }

  // 파일 존재 여부 확인 (HEAD 요청)
  try {
    const url = `${AUDIO_BASE}${filename}`
    const res = await fetch(url, { method: 'HEAD' })
    if (!res.ok) return null
    _urlCache.set(filename, url)
    return new Audio(url)
  } catch {
    return null
  }
}
