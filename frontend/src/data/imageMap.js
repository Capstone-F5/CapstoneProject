// 백엔드 시드 데이터(backend/core/seed.py)의 name_ko 문자열 → 기존 정적 이미지 경로 매핑.
// 이름에 공백/약어 차이가 있어(예: "감자튀김(M)" vs 파일명 "감튀.webp") fuzzy 매칭 대신
// 명시적 테이블로 관리한다. 매칭 안 되면 null → 호출부가 기존 이모지 폴백을 사용한다.

const BURGER_IMAGES = {
  'F 버거':          '/images/burgers/F버거.webp',
  '그릴드 비프 버거':  '/images/burgers/그릴드비프버거.webp',
  '모짜렐라 버거':     '/images/burgers/모짜렐라버거.webp',
  '비건 버거':         '/images/burgers/비건버거.webp',
  '게살 버거':         '/images/burgers/게살버거.webp',
  '치킨 다릿살 버거':   '/images/burgers/치킨다릿살버거.webp',
  '더블 불고기 버거':   '/images/burgers/더블불고기버거.webp',
  '치킨 가슴살 버거':   '/images/burgers/치킨가슴살버거.webp',
  '새우 버거':         '/images/burgers/새우버거.webp',
  '불고기 버거':       '/images/burgers/불고기버거.webp',
  '치즈 버거':         '/images/burgers/치즈버거.webp',
  '데리버거':          '/images/burgers/데리버거.webp',
  // '더블 치즈 버거'는 대응하는 이미지 에셋이 없어 이모지 폴백 사용
}

const SET_IMAGES = {
  'F 버거':          '/images/sets/F버거 세트.webp',
  '그릴드 비프 버거':  '/images/sets/그릴드비프버거 세트.webp',
  '모짜렐라 버거':     '/images/sets/모짜렐라버거 세트.webp',
  '비건 버거':         '/images/sets/비건버거 세트.webp',
  '게살 버거':         '/images/sets/게살버거 세트.webp',
  '치킨 다릿살 버거':   '/images/sets/치킨다릿살버거 세트.webp',
  '더블 불고기 버거':   '/images/sets/더블불고기버거 세트.webp',
  '치킨 가슴살 버거':   '/images/sets/치킨가슴살버거 세트.webp',
  '새우 버거':         '/images/sets/새우버거 세트.webp',
  '불고기 버거':       '/images/sets/불고기버거 세트.webp',
  '치즈 버거':         '/images/sets/치즈버거 세트.webp',
  '데리버거':          '/images/sets/데리버거 세트.webp',
}

const SIDE_IMAGES = {
  '양념감자튀김':   '/images/sides/양념감튀.webp',
  '너겟(4조각)':    '/images/sides/너겟.webp',
  '치즈스틱(2개)':  '/images/sides/치즈스틱.webp',
  '감자튀김(M)':    '/images/sides/감튀.webp',
  '콘샐러드':       '/images/sides/콘샐러드.webp',
  '코울슬로':       '/images/sides/코울슬로.webp',
}

const DRINK_IMAGES = {
  '오렌지 주스':    '/images/drinks/오렌지주스.webp',
  '콜라(M)':        '/images/drinks/콜라.webp',
  '제로 콜라(M)':   '/images/drinks/콜라.webp',
  '사이다(M)':      '/images/drinks/사이다.webp',
  '제로 사이다(M)': '/images/drinks/사이다.webp',
  '뽀로로 음료수':  '/images/drinks/뽀로로음료.webp',
  '생수':           '/images/drinks/생수.webp',
}

const ALL_IMAGES = { ...BURGER_IMAGES, ...SIDE_IMAGES, ...DRINK_IMAGES }

export function lookupImage(nameKo) {
  return ALL_IMAGES[nameKo] ?? null
}

export function lookupSetImage(nameKo) {
  return SET_IMAGES[nameKo] ?? null
}
