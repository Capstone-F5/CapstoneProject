# 음성(LLM) 기반 주문 제어 기능 설계서

> 목표: 사용자가 GPT와 **음성으로 대화**하여 메뉴를 담고, 수정하고, 결제 화면까지 진행할 수 있도록 한다.
> 복합 발화("불고기버거 2개랑 콜라 하나 주고 양상추는 빼줘, 그리고 결제할게")를 한 번에 이해해 여러 동작을 순차 실행한다.

작성일: 2026-05-30

---

## 1. 이 문서의 범위

- **포함**: 음성 발화 → 장바구니 추가/수정/삭제 → 화면 전환(결제 진입)까지의 아키텍처와 단계별 구현 계획
- **불포함**: 실제 PG 연동(현재 MOCK_PG 유지), 신규 메뉴 추가, 디자인 시안

---

## 2. 핵심 문제: "장바구니가 두 개"다

현재 시스템에는 **서로 동기화되지 않는 장바구니가 두 개** 존재한다. 이 기능을 구현하려면 이 문제를 먼저 해결해야 한다.

| 구분 | 프론트엔드 장바구니 | 백엔드 DB 장바구니 |
|------|--------------------|-------------------|
| 위치 | `App.jsx`의 React state (`cart`) | `CART_ITEMS` 테이블 |
| 조작 | `addToCart` / `updateQty` / `clearCart` | LLM 도구 `add_to_cart` / `approve_payment` |
| **메뉴 ID** | **숫자 (1~23)**, `menuData.js` 정적 파일 | **UUID (36자)**, DB seed |
| 화면 표시 | ✅ CartScreen이 이걸 그림 | ❌ 화면에 안 보임 |
| 누가 보나 | 사용자(화면) | LLM(도구 호출) |

### 무엇이 문제인가

현재 구조에서 사용자가 음성으로 "불고기버거 주세요"라고 하면:

1. LLM이 `add_to_cart`(UUID 기반)를 호출 → **DB 장바구니**에 추가됨
2. 하지만 화면의 CartScreen은 **React state 장바구니**를 그림
3. → **음성으로 담은 메뉴가 화면에 안 보인다.** 화면에서 담은 메뉴는 LLM이 모른다.

게다가 두 장바구니의 메뉴 ID 체계가 달라서(`1` vs `a3f9...`) 단순 연결도 불가능하다.

> **결론: 두 장바구니를 하나로 합치는 것이 이 기능의 전제 조건이다.**

---

## 3. 설계 방향 결정

### 선택지

**(A) 프론트엔드 장바구니를 단일 진실 공급원(SoT)으로 — LLM은 "동작 지시"만 발행** ⭐ 권장
- LLM은 DB에 직접 쓰지 않는다. 대신 `add_item`, `update_qty`, `navigate` 같은 **구조화된 액션(intent)** 을 반환한다.
- 프론트엔드가 이 액션을 받아 기존 `addToCart` / `updateQty` / `nav` 를 실행한다.
- 음성은 **기존 UI를 조작하는 리모컨**이 된다. 기존 화면/결제 흐름을 그대로 재사용.

**(B) 백엔드 DB를 단일 진실 공급원으로 — 프론트가 DB 장바구니를 읽음**
- Cart 조회/수정 REST API를 신설하고, CartScreen을 DB 장바구니의 뷰로 재작성.
- 화면에서 담는 동작도 전부 DB에 쓰도록 변경.
- 단일 소스라 깔끔하지만, **프론트 전면 재작성**이 필요하고 캡스톤 일정에 부담.

### 권장: (A) 액션 발행 방식

이유:
- 프론트엔드에 **이미 완성된 주문→장바구니→결제→완료 흐름**이 있다. 이걸 버리지 않는다.
- 화면 터치 주문과 음성 주문이 **같은 React state** 를 공유하므로 자연히 일관된다.
- `navigate` 액션으로 화면 전환(결제 진입)도 동일한 메커니즘으로 처리된다.
- 복합 발화는 **액션 배열**로 자연스럽게 표현된다(한 턴에 여러 액션).

이하 설계는 모두 **(A) 기준**이다.

---

## 4. 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                         사용자 (음성)                          │
└───────────────────────────┬──────────────────────────────────┘
                            │ 발화
                  ┌─────────▼─────────┐
                  │  Silero VAD + STT │  (기존)
                  └─────────┬─────────┘
                            │ 텍스트
        ┌───────────────────▼────────────────────┐
        │  POST /ai_modules/llm/stream            │
        │  body: {                                │
        │    session_id, input, language,         │
        │    cart: [현재 장바구니 스냅샷],  ← 신규  │
        │    screen: "menu"               ← 신규  │
        │  }                                      │
        └───────────────────┬────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  LLM Agent (의도 해석기)     │
              │  - 메뉴 검색(읽기 전용)      │
              │  - 액션 생성 (DB 안 씀)      │
              └─────────────┬──────────────┘
                            │ SSE
        ┌───────────────────▼─────────────────────┐
        │  스트림 이벤트:                            │
        │  data:{token:"..."}        ← 음성 답변     │
        │  data:{action:{type,...}}  ← 동작 지시 신규 │
        │  data:{done:true, output}                 │
        └───────────────────┬─────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  ChatPanel (액션 디스패처)   │
              │  onAction(action) →         │
              └─────────────┬──────────────┘
                            │ 콜백
              ┌─────────────▼──────────────┐
              │  App.jsx                    │
              │  addToCart / updateQty /    │
              │  clearCart / nav            │  ← 기존 함수 재사용
              └─────────────┬──────────────┘
                            │
                   ┌────────▼────────┐
                   │  화면 즉시 갱신   │  + TTS로 답변 음성 재생
                   └─────────────────┘
```

핵심 변화 2가지:
1. **요청에 현재 장바구니/화면 상태를 같이 보낸다** → LLM이 "수정/삭제"와 "결제 전 확인"을 할 수 있다.
2. **응답에 액션을 같이 보낸다** → 프론트가 화면을 조작한다.

---

## 5. 액션 프로토콜 명세

LLM이 발행하고 프론트가 실행하는 표준 액션. 한 턴에 **여러 개**가 순서대로 올 수 있다.

```jsonc
// 1. 메뉴 담기
{ "type": "add_item",
  "menu_id": 2,            // 프론트 menuData 숫자 ID
  "name": "불고기버거",     // 검증/표시용
  "item_type": "single",   // "single" | "set"
  "quantity": 2,
  "exclusion": "양상추 제외",// menuData.exclusions 중 하나, 없으면 "없음"
  "side": null,            // 세트일 때 SET_SIDES 이름
  "drink": null,           // 세트일 때 SET_DRINKS 이름
  "special_note": "반으로 잘라주세요"  // 배리어프리 비정형 요구(주방 전달)
}

// 2. 수량 변경
{ "type": "update_qty", "cart_id": 1717..., "quantity": 3 }
// 또는 메뉴 식별로:
{ "type": "update_qty", "match": { "menu_id": 17 }, "quantity": 1 }

// 3. 삭제
{ "type": "remove_item", "match": { "menu_id": 17 } }

// 4. 전체 비우기
{ "type": "clear_cart" }

// 5. 화면 전환
{ "type": "navigate", "screen": "cart" }   // start|orderType|menu|cart|payment

// 6. 결제 진행 (결제 화면 진입 + 수단 지정)
{ "type": "checkout", "method": "card" }   // card|cash|pay (선택)
```

> 프론트는 알 수 없는 `type`이 오면 **무시**하고 로그만 남긴다(전방 호환).

---

## 6. 요청/응답 계약 변경

### 6.1 요청 (프론트 → 백엔드)

```jsonc
POST /ai_modules/llm/stream
{
  "session_id": "...",
  "input": "불고기버거 두 개 주세요",
  "language": "ko",
  "cart": [                          // ← 신규: 현재 화면 장바구니 스냅샷
    { "cart_id": 171.., "menu_id": 5, "name": "치즈버거",
      "item_type": "single", "quantity": 1, "unit_price": 4200,
      "exclusion": "없음", "side": null, "drink": null }
  ],
  "screen": "menu"                   // ← 신규: 현재 화면 (맥락 판단용)
}
```

장바구니를 매 요청에 실어 보내므로 별도 `get_cart` DB 조회가 불필요해진다.
LLM은 전달받은 `cart`를 보고 "이미 담긴 것 / 수정 대상 / 결제 가능 여부"를 판단한다.

### 6.2 응답 (백엔드 → 프론트, SSE)

기존 토큰 스트림에 `action` 이벤트를 추가한다.

```
data: {"token": "불고기버거 두 개 "}
data: {"token": "담아드릴게요."}
data: {"action": {"type": "add_item", "menu_id": 2, "quantity": 2, ...}}
data: {"action": {"type": "navigate", "screen": "cart"}}
data: {"done": true, "output": "불고기버거 두 개 담아드릴게요."}
```

---

## 7. LLM 레이어 변경

### 7.1 메뉴 데이터 통합 (전제 작업)

LLM이 **프론트와 같은 숫자 ID**를 산출해야 한다. 방법:

- `menuData.js` 와 동일한 카탈로그를 백엔드가 참조할 수 있는 **단일 JSON**(`shared/menu_catalog.json` 등)으로 추출
- 프론트는 이 JSON을 import, 백엔드 RAG/검색 도구도 이 JSON으로 인덱싱
- 이렇게 하면 `search_menu`가 반환하는 `menu_id`가 곧 프론트 `addToCart`에 쓰이는 ID가 된다

> 대안: 당장은 메뉴 수가 23개로 적으므로, **카탈로그 전체를 시스템 프롬프트에 주입**하고 RAG를 생략해도 된다(토큰 부담 적음). RAG는 메뉴가 많아질 때 재도입.

### 7.2 도구 재설계

기존 4개 도구의 **부수효과(DB 쓰기)를 제거**하고 액션 생성기로 바꾼다.

| 기존 | 변경 후 |
|------|---------|
| `search_menu` (RAG, DB) | `search_menu` (공유 카탈로그 읽기 전용) — 유지 |
| `add_to_cart` (DB INSERT) | `add_item` 액션을 큐에 적재 |
| `get_cart` (DB SELECT) | **삭제** — 장바구니는 요청 body로 전달됨 |
| `approve_payment` (DB 트랜잭션) | `checkout` 액션을 큐에 적재 (실제 주문 생성은 프론트 결제 흐름이 담당) |
| (없음) | `update_qty`, `remove_item`, `navigate` 신규 |

`run_agent_stream`은 도구 호출로 쌓인 액션을 모아 SSE의 `action` 이벤트로 흘려보낸다.

### 7.3 프롬프트 변경 (복합 발화 + 안전)

시스템 프롬프트에 추가할 규칙:
- "한 발화에 여러 요청이 섞여 있으면, **필요한 액션을 순서대로 모두** 생성하라."
- "메뉴/가격은 반드시 카탈로그(또는 `search_menu`)로 확인한 ID만 사용하라(할루시네이션 금지)."
- 배리어프리: 정형 옵션(양상추 제외 등)은 `exclusion`, 비정형("반으로 잘라줘")은 `special_note`로 분리 — **기존 규칙 유지**.
- 결제 안전장치: "결제 의사가 보이면, 전달받은 `cart`가 비어있지 않은지 확인하고, **사용자에게 품목·총액을 한 번 복창한 뒤** `checkout` 액션을 생성하라."

---

## 8. 프론트엔드 변경

### 8.1 `ChatPanel.jsx`
- 요청 body에 `cart`, `screen` 추가 (props로 받음)
- SSE 파싱에 `data.action` 분기 추가 → `props.onAction(action)` 호출
- 토큰은 지금처럼 말풍선에 누적

### 8.2 `App.jsx`
- `<ChatPanel>` 에 `cart`, `screen`, `onAction` 전달
- `onAction(action)` 핸들러에서 액션 타입별로 기존 함수 호출:

```jsx
const handleVoiceAction = (a) => {
  switch (a.type) {
    case 'add_item':    addToCart(buildCartItem(a)); break;  // menuData로 unit_price 등 보강
    case 'update_qty':  updateQty(resolveCartId(a), a.quantity); break;
    case 'remove_item': updateQty(resolveCartId(a), 0); break;
    case 'clear_cart':  clearCart(); break;
    case 'navigate':    nav(a.screen); break;
    case 'checkout':    nav('cart'); /* 또는 결제 팝업 오픈 */ break;
  }
}
```

- `buildCartItem(a)`: 액션의 `menu_id`로 `menuData`를 조회해 `name/unitPrice/image/exclusion/side/drink` 를 채워 기존 cart 아이템 형태로 변환(세트면 `setSurcharge`, 사이드/음료 extra 반영).
- `resolveCartId(a)`: `cart_id` 직접 지정이 없으면 `match`(menu_id 등)로 현재 cart에서 찾음.

### 8.3 결제 진입
- `checkout` 액션 → `nav('cart')` 후 결제 팝업 자동 오픈, 또는 `method`가 있으면 해당 결제 대기 화면으로.
- **실제 주문 생성/결제는 기존 CartScreen의 `handleComplete`(createOrder→processPayment) 흐름을 재사용** — 음성은 거기까지 "데려다주는" 역할.

---

## 9. 복합 발화 처리 예시

### 예시 1 — 한 발화에 추가 2종 + 옵션 + 결제
> "불고기버거 두 개랑 콜라 하나 주고, 버거는 양상추 빼줘. 그리고 결제할게"

LLM이 생성하는 액션 시퀀스:
```jsonc
[ {"type":"add_item","menu_id":2,"quantity":2,"exclusion":"양상추 제외"},
  {"type":"add_item","menu_id":17,"quantity":1},
  {"type":"navigate","screen":"cart"},
  {"type":"checkout"} ]
```
답변(TTS): "불고기버거 두 개는 양상추 빼고, 콜라 하나 담았어요. 총 11,000원입니다. 결제 도와드릴게요."

### 예시 2 — 수정
> "아까 콜라는 빼고 사이다로 바꿔줘"

전달된 `cart`에서 콜라(menu_id 17)를 찾아:
```jsonc
[ {"type":"remove_item","match":{"menu_id":17}},
  {"type":"add_item","menu_id":19,"quantity":1} ]
```

### 예시 3 — 배리어프리 비정형
> "치즈버거 하나, 손이 불편하니까 반으로 잘라서 주세요"
```jsonc
[ {"type":"add_item","menu_id":5,"quantity":1,"special_note":"반으로 잘라서 주세요"} ]
```

---

## 10. 안전장치 & 엣지 케이스

| 상황 | 처리 |
|------|------|
| 결제인데 장바구니 비어있음 | LLM이 `checkout` 대신 "담긴 메뉴가 없어요" 안내 |
| 모호한 메뉴("버거 줘") | LLM이 되묻기(질문), 액션 미발행 |
| 존재하지 않는 메뉴 | 카탈로그에 없으면 추가 거부 + 유사 메뉴 추천 |
| 액션-답변 불일치 | 답변 텍스트는 실제 발행한 액션과 일치하도록 프롬프트 강제 |
| 결제 전 확인 | `checkout` 직전 품목·총액 복창 (오발화 결제 방지) |
| 중복 추가 | 프론트 `addToCart`가 동일 구성은 수량만 증가(기존 로직) → 자연 처리 |
| 세션/언어 리셋 | 기존 `kiosk-session-reset` 이벤트와 연동 (대기화면 복귀 시 초기화) |

---

## 11. 단계별 구현 로드맵

### Phase 0 — 메뉴 데이터 통합 (전제)
- [ ] `menuData.js`를 공유 카탈로그로 추출(또는 백엔드에서 동일 데이터 보유)
- [ ] LLM이 프론트 숫자 ID를 산출하도록 검색/프롬프트 정비

### Phase 1 — 액션 파이프라인 (담기)
- [ ] 백엔드: 액션 큐 + SSE `action` 이벤트 추가, `add_item` 도구
- [ ] 요청 body에 `cart`/`screen` 수용
- [ ] 프론트: `ChatPanel` 액션 파싱 + `App.handleVoiceAction`(`add_item`만)
- [ ] 검증: "치즈버거 하나 줘" → 화면 장바구니에 즉시 반영

### Phase 2 — 수정/삭제
- [ ] `update_qty`, `remove_item`, `clear_cart` 도구 + 핸들러
- [ ] `match` 해석(menu_id로 cart 라인 찾기)
- [ ] 검증: "콜라 빼줘", "버거 3개로 늘려줘"

### Phase 3 — 화면 전환 / 결제 진입
- [ ] `navigate`, `checkout` 도구 + 핸들러
- [ ] 결제 전 복창 + 빈 장바구니 가드
- [ ] 검증: "이대로 결제할게" → 장바구니/결제 화면 진입

### Phase 4 — 복합 발화 다듬기
- [ ] 프롬프트로 다중 액션 순서 보장
- [ ] 예시 1~3 시나리오 통합 테스트
- [ ] special_note 배리어프리 동작 확인

### Phase 5 (선택) — DB 영속화
- [ ] 최종 결제 시점에만 ORDER/ORDER_ITEMS/PAYMENT 기록(special_note 포함)으로 주방 전달 복원

---

## 12. 결정이 필요한 사항

1. **메뉴 소스 통합 방식**: 공유 JSON 추출 vs 프롬프트 주입(RAG 생략) — Phase 0의 방향.
2. **`checkout` 액션의 도달점**: 장바구니 화면까지만 데려다줄지, 결제수단 선택까지 자동화할지(오결제 리스크).
3. **DB 영속화 시점**(Phase 5): 음성 주문도 주방 전달(special_note)이 필요하면 결제 시 DB 기록 복원 여부.
4. **전략 (A) vs (B)** 최종 확정: 본 문서는 (A) 권장. (B)를 택하면 프론트 장바구니를 DB 뷰로 재작성해야 함.

---

## 부록 A. 현재 코드 기준점

- 프론트 장바구니/네비: `frontend/src/App.jsx` (`addToCart`/`updateQty`/`clearCart`/`nav`)
- 메뉴 데이터: `frontend/src/data/menuData.js` (숫자 ID 1~23, `SET_SIDES`/`SET_DRINKS`/`setSurcharge`)
- 음성 패널: `frontend/src/components/ChatPanel.jsx` (STT/LLM 스트림/TTS)
- LLM 도구: `ai_modules/llm/tools.py` (현재 4개, DB 기반)
- LLM 실행: `backend/core/llm_service.py` (`run_agent_stream`)
- LLM 엔드포인트: `backend/api/llm.py` (`/ai_modules/llm/stream`)
- 프롬프트: `ai_modules/llm/prompts.py`
- DB 스키마: `backend/core/models.py` (`CART_ITEMS`/`ORDER_ITEMS`의 `special_note`)
