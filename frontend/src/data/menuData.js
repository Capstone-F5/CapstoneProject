export const categories = [
  { id: 'recommended', name: '추천메뉴', emoji: '🍱' },
  { id: 'burger',      name: '버거',    emoji: '🍔' },
  { id: 'side',        name: '사이드',  emoji: '🍟' },
  { id: 'drink',       name: '음료수',  emoji: '🥤' },
]

export const menuItems = {
  recommended: [
    { id: 1,  name: 'F버거',    price: 7500, kcal: 820,  desc: '"치킨과 불고기의 만남, 한 입에 끝내는 환상의 더블 콤보!"', hasSet: true,  exclusions: ['없음', '양상추 제외', '양파 제외'], image: '/images/burgers/F버거.png',    setImage: '/images/sets/F버거 세트.png' },
    { id: 9,  name: '게살버거', price: 5000, kcal: null, desc: '풍성한 게살과 크림 소스의 조화',                           hasSet: true,  exclusions: ['없음', '소스 제외'],               image: '/images/burgers/게살버거.png', setImage: '/images/sets/게살버거 세트.png' },
    { id: 10, name: '비건버거', price: 6800, kcal: null, desc: '신선한 채소와 식물성 패티',                               hasSet: true,  exclusions: ['없음'],                            image: '/images/burgers/비건버거.png', setImage: '/images/sets/비건버거 세트.png' },
  ],
  burger: [
    { id: 1,  name: 'F버거',          price: 7500, kcal: 820,  desc: '"치킨과 불고기의 만남, 한 입에 끝내는 환상의 더블 콤보!"', hasSet: true, exclusions: ['없음', '양상추 제외', '양파 제외'], image: '/images/burgers/F버거.png',          setImage: '/images/sets/F버거 세트.png' },
    { id: 2,  name: '불고기버거',     price: 4500, kcal: null, desc: '부드러운 불고기 패티',                                   hasSet: true, exclusions: ['없음', '양상추 제외'],             image: '/images/burgers/불고기버거.png',     setImage: '/images/sets/불고기버거 세트.png' },
    { id: 3,  name: '더블불고기버거', price: 6000, kcal: null, desc: '두 배로 즐기는 불고기의 풍미',                          hasSet: true, exclusions: ['없음', '양상추 제외'],             image: '/images/burgers/더블불고기버거.png', setImage: '/images/sets/더블불고기버거 세트.png' },
    { id: 4,  name: '새우버거',       price: 4800, kcal: null, desc: '통통한 새우 패티',                                      hasSet: true, exclusions: ['없음', '소스 제외'],               image: '/images/burgers/새우버거.png',       setImage: '/images/sets/새우버거 세트.png' },
    { id: 5,  name: '치즈버거',       price: 4200, kcal: null, desc: '진한 치즈와 비프 패티',                                 hasSet: true, exclusions: ['없음', '양파 제외'],               image: '/images/burgers/치즈버거.png',       setImage: '/images/sets/치즈버거 세트.png' },
    { id: 6,  name: '치킨다릿살버거', price: 6200, kcal: null, desc: '바삭한 치킨 다릿살',                                   hasSet: true, exclusions: ['없음', '양상추 제외'],             image: '/images/burgers/치킨다릿살버거.png', setImage: '/images/sets/치킨다릿살버거 세트.png' },
    { id: 7,  name: '치킨가슴살버거', price: 5500, kcal: null, desc: '담백한 치킨 가슴살',                                   hasSet: true, exclusions: ['없음', '양상추 제외'],             image: '/images/burgers/치킨가슴살버거.png', setImage: '/images/sets/치킨가슴살버거 세트.png' },
    { id: 8,  name: '데리버거',       price: 4000, kcal: null, desc: '달콤한 데리야끼 소스',                                  hasSet: true, exclusions: ['없음'],                            image: '/images/burgers/데리버거.png',       setImage: '/images/sets/데리버거 세트.png' },
    { id: 9,  name: '게살버거',       price: 5000, kcal: null, desc: '풍성한 게살과 크림 소스의 조화',                        hasSet: true, exclusions: ['없음', '소스 제외'],               image: '/images/burgers/게살버거.png',       setImage: '/images/sets/게살버거 세트.png' },
    { id: 10, name: '비건버거',       price: 6800, kcal: null, desc: '신선한 채소와 식물성 패티',                             hasSet: true, exclusions: ['없음'],                            image: '/images/burgers/비건버거.png',       setImage: '/images/sets/비건버거 세트.png' },
    { id: 11, name: '모짜렐라버거',   price: 7200, kcal: null, desc: '쭉쭉 늘어나는 모짜렐라 치즈',                          hasSet: true, exclusions: ['없음'],                            image: '/images/burgers/모짜렐라버거.png',   setImage: '/images/sets/모짜렐라버거 세트.png' },
    { id: 12, name: '그릴드비프버거', price: 7800, kcal: null, desc: '불향 가득한 그릴드 비프 패티',                         hasSet: true, exclusions: ['없음', '양파 제외'],               image: '/images/burgers/그릴드비프버거.png', setImage: '/images/sets/그릴드비프버거 세트.png' },
  ],
  side: [
    { id: 13, name: '감자튀김',   price: 2000, kcal: null, desc: '바삭한 황금 감자튀김',  hasSet: false, exclusions: [], image: '/images/sides/감튀.png' },
    { id: 14, name: '치즈스틱',   price: 2000, kcal: null, desc: '쭉 늘어나는 치즈스틱',  hasSet: false, exclusions: [], image: '/images/sides/치즈스틱.png' },
    { id: 15, name: '치킨너겟',   price: 3000, kcal: null, desc: '바삭한 치킨너겟 4조각', hasSet: false, exclusions: [], image: '/images/sides/너겟.png' },
    { id: 16, name: '양념감자튀김', price: 2500, kcal: null, desc: '매콤달콤 양념 감자튀김', hasSet: false, exclusions: [], image: '/images/sides/양념감튀.png' },
  ],
  drink: [
    { id: 17, name: '코카콜라',    price: 2000, kcal: null, desc: '', hasSet: false, exclusions: [], image: '/images/drinks/콜라.png' },
    { id: 18, name: '코카콜라제로', price: 2000, kcal: null, desc: '', hasSet: false, exclusions: [], image: '/images/drinks/콜라.png' },
    { id: 19, name: '사이다',      price: 2500, kcal: null, desc: '', hasSet: false, exclusions: [], image: '/images/drinks/사이다.png' },
    { id: 20, name: '사이다제로',  price: 2000, kcal: null, desc: '', hasSet: false, exclusions: [], image: '/images/drinks/사이다.png' },
    { id: 21, name: '생수',        price: 1000, kcal: null, desc: '', hasSet: false, exclusions: [], image: '/images/drinks/생수.png' },
    { id: 22, name: '오렌지주스',  price: 2500, kcal: null, desc: '', hasSet: false, exclusions: [], image: '/images/drinks/오렌지주스.png' },
    { id: 23, name: '뽀로로음료수', price: 2000, kcal: null, desc: '', hasSet: false, exclusions: [], image: '/images/drinks/뽀로로음료.png' },
  ],
}

export const SET_SIDES = [
  { name: '감자튀김',    extra: 0,   image: '/images/sides/감튀.png' },
  { name: '치즈스틱',    extra: 0,   image: '/images/sides/치즈스틱.png' },
  { name: '치킨너겟',    extra: 0,   image: '/images/sides/너겟.png' },
  { name: '양념감자튀김', extra: 500, image: '/images/sides/양념감튀.png' },
]

export const SET_DRINKS = [
  { name: '콜라',       extra: 0,   image: '/images/drinks/콜라.png' },
  { name: '제로콜라',   extra: 0,   image: '/images/drinks/콜라.png' },
  { name: '사이다',     extra: 0,   image: '/images/drinks/사이다.png' },
  { name: '제로사이다', extra: 0,   image: '/images/drinks/사이다.png' },
  { name: '생수',       extra: 0,   image: '/images/drinks/생수.png' },
  { name: '뽀로로음료', extra: 0,   image: '/images/drinks/뽀로로음료.png' },
  { name: '오렌지주스', extra: 500, image: '/images/drinks/오렌지주스.png' },
]

export const SET_SURCHARGE = 2000
