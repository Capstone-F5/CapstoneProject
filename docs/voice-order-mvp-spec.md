# 음성 주문 제어 — MVP 구현 사양서

> 상위 설계: [voice-order-control-design.md](voice-order-control-design.md)
> 본 문서는 그 중 **MVP 범위만** 구현 가능한 수준으로 구체화한 것이다.

작성일: 2026-05-30

---

## 0. MVP 확정 사항

| 항목 | 결정 |
|------|------|
| 전략 | **(A) 액션 발행** — 프론트 React 장바구니가 단일 진실 공급원 |
| DB | **연결 안 함** — 대화/장바구니/결제 모두 프론트 메모리에서만 |
| 메뉴 소스 | **프롬프트에 카탈로그 주입** (RAG/FAISS/DB 생략, 메뉴 23개라 토큰 부담 적음) |
| `checkout` 도달점 | **`cart` 화면으로 이동**까지. 실제 결제 승인은 기존 결제 팝업에서 사람이 확인 (오결제 방지) |
| 기존 DB 도구 | `tools.py`는 보존하되 MVP 스트리밍 경로에서 **미사용** (Phase 5에서 복원) |

MVP가 끝나면 사용자는 음성만으로 **담기 / 수정 / 삭제 / 비우기 / 장바구니·결제 화면 이동**을 할 수 있다.

---

## 1. 정확한 장바구니 아이템 스키마 (구현 기준점)

`ItemDetailModal.handleAdd` → `App.addToCart`가 만드는 실제 객체. 음성 액션도 **이 형태로 변환**해야 화면과 호환된다.

```js
{
  id: 2,                 // menuData 숫자 ID
  name: '불고기버거',
  image: '/images/burgers/불고기버거.webp',  // 세트면 setImage
  type: 'single',        // 'single' | 'set'
  qty: 2,
  unitPrice: 4500,       // 아래 공식으로 계산
  exclusion: '양상추 제외',// menuData.exclusions 중 하나, 기본 '없음'
  side: null,            // 세트면 SET_SIDES[].name
  sideExtra: 0,          // 세트면 해당 side.extra
  drink: null,           // 세트면 SET_DRINKS[].name
  drinkExtra: 0,         // 세트면 해당 drink.extra
  // ↓ addToCart가 자동 부여 (직접 넣지 않음)
  key: '2-single-양상추 제외--',
  cartId: 1717000000000.12,
}
```

**unitPrice 계산식** (ItemDetailModal과 동일하게 맞춰야 함):
```
unitPrice = item.price
          + (type==='set' ? SET_SURCHARGE(2000) : 0)
          + (type==='set' ? side.extra + drink.extra : 0)
```

**세트 옵션 데이터** (`menuData.js`):
- `SET_SIDES`: 감자튀김(+0), 치즈스틱(+0), 치킨너겟(+0), 양념감자튀김(+500)
- `SET_DRINKS`: 콜라(+0), 제로콜라(+0), 사이다(+0), 제로사이다(+0), 생수(+0), 뽀로로음료(+0), 오렌지주스(+500)
- `SET_SURCHARGE`: 2000
- 세트인데 side/drink 미지정 → **기본값 첫 항목**(감자튀김/콜라) 사용

**addToCart 병합 규칙**: `key`가 같으면(같은 id·type·exclusion·side·drink) 수량만 누적. 음성으로 같은 구성 또 담으면 자연히 수량 증가.

**updateQty(cartId, qty)**: `qty<=0`이면 삭제, 아니면 수량 교체.

---

## 2. 액션 프로토콜 (MVP 6종)

LLM이 발행 → 프론트가 실행. 한 턴에 여러 개가 **순서대로** 올 수 있다.

```jsonc
// 담기
{ "type":"add_item", "menu_id":2, "name":"불고기버거",
  "item_type":"single",            // "single"|"set"
  "quantity":2,
  "exclusion":"양상추 제외",         // 생략 시 "없음"
  "side":null, "drink":null,        // item_type=="set"일 때만 의미
  "special_note":"반으로 잘라주세요" // 배리어프리(주방 전달), 생략 가능
}

// 수량 변경 — match로 현재 장바구니 라인 식별
{ "type":"update_qty", "match":{"menu_id":17}, "quantity":3 }

// 삭제
{ "type":"remove_item", "match":{"menu_id":17} }

// 전체 비우기
{ "type":"clear_cart" }

// 화면 이동
{ "type":"navigate", "screen":"cart" }   // menu|cart 등

// 결제 진행 (cart 화면으로 이동; method는 참고용, 자동 결제는 안 함)
{ "type":"checkout", "method":"card" }    // method 생략 가능
```

### match 해석 규칙 (프론트)
1. `match.cart_id` 있으면 그걸로 직접 식별
2. 없고 `match.menu_id` 있으면 현재 cart에서 그 `id`의 라인 검색
   - 여러 개면(옵션 다른 동일 메뉴) → **가장 마지막에 담긴 것** 1개 (MVP 단순화)
3. 못 찾으면 액션 무시 + 콘솔 경고

### 알 수 없는 type
프론트는 무시하고 로그만 남긴다(전방 호환).

---

## 3. 요청/응답 계약 변경

### 3.1 요청 (프론트 → 백엔드)
```jsonc
POST /ai_modules/llm/stream
{
  "session_id":"...",
  "input":"불고기버거 두 개 주세요",
  "language":"ko",
  "screen":"menu",                  // ← 신규: 현재 화면(맥락)
  "cart":[                          // ← 신규: 현재 장바구니 스냅샷
    { "cart_id":1717.., "menu_id":5, "name":"치즈버거",
      "item_type":"single", "quantity":1, "unit_price":4200,
      "exclusion":"없음", "side":null, "drink":null }
  ]
}
```
장바구니를 매 요청에 실어 보내므로 `get_cart` DB 조회가 불필요. LLM은 이 `cart`를 보고 수정/삭제 대상과 결제 가능 여부를 판단한다.

### 3.2 응답 (SSE) — 토큰 + 액션 혼합
```
data: {"token":"불고기버거 두 개 "}
data: {"token":"담아드릴게요."}
data: {"action":{"type":"add_item","menu_id":2,"quantity":2,...}}
data: {"action":{"type":"navigate","screen":"cart"}}
data: {"done":true,"output":"불고기버거 두 개 담아드릴게요."}
```

---

## 4. 백엔드 구현 계획

### 4.1 신규 파일

**`ai_modules/llm/menu_catalog.py`**
- `menuData.js`를 미러링한 파이썬 카탈로그(숫자 ID 1~23 + 옵션 + 세트 데이터)
- `MENU_CATALOG`: 리스트(각 항목 id/name/price/category/hasSet/exclusions)
- `SET_SIDES/SET_DRINKS/SET_SURCHARGE`
- `render_catalog_for_prompt() -> str`: 프롬프트에 끼울 사람이 읽는 메뉴표 문자열
- ⚠️ **단일 소스 동기화 주의**: `menuData.js`와 값이 어긋나면 음성 주문이 깨짐. 주석으로 "menuData.js와 동기화" 명시. (Phase 5에서 공유 JSON으로 일원화 검토)

**`ai_modules/llm/action_context.py`**
- `session_context.py`와 같은 ContextVar 패턴
- `set_cart(cart: list)`, `get_cart()` — 요청의 장바구니 스냅샷 보관
- `reset_actions()`, `push_action(dict)`, `get_actions() -> list` — 도구가 발행한 액션 수집

**`ai_modules/llm/action_tools.py`** (DB 미사용, 액션 발행만)
- `add_item`, `update_qty`, `remove_item`, `clear_cart`, `navigate`, `checkout` 6개 도구
- 각 도구는: 입력 검증(카탈로그·현재 cart 대조) → `push_action({...})` → 사람이 읽을 확인 문자열 반환
  - 예: `add_item`은 `menu_id`가 카탈로그에 있는지 확인, 세트 옵션 기본값 보정 후 액션 push, "불고기버거(단품) 2개 담음" 반환
- `ACTION_TOOLS` 리스트로 export

### 4.2 수정 파일

**`ai_modules/llm/agent.py`**
- `build_agent_executor()`가 `ACTION_TOOLS`를 사용하도록 전환 (기존 `TOOLS` 대신)
- 시스템 프롬프트에 `render_catalog_for_prompt()` 결과를 합성
- 싱글톤 유지

**`ai_modules/llm/prompts.py`** — 시스템 프롬프트 개정
- 역할: "음성으로 장바구니를 조작하는 도우미"
- 규칙 추가:
  - 메뉴 ID는 **반드시 주입된 카탈로그의 숫자 ID만** 사용 (할루시네이션 금지)
  - 한 발화에 여러 요청이 섞이면 **필요한 도구를 순서대로 모두 호출**
  - 정형 옵션(양상추 제외 등) → `exclusion`, 비정형("반으로 잘라줘") → `special_note` (기존 배리어프리 규칙 유지)
  - 결제 의사 → 전달받은 `cart`가 비어있지 않은지 보고, **품목·총액을 복창한 뒤** `checkout` 호출. 비어있으면 안내만.
  - 모호하면(예: "버거 줘") 되묻기, 도구 호출 안 함
- 현재 장바구니를 프롬프트(또는 human 메시지 앞)에 주입: `get_cart()` 결과를 요약해 삽입

**`backend/core/llm_service.py`** — `run_agent_stream` 개정
1. `set_session_id` + **`set_cart(req.cart)`** + `reset_actions()`
2. 현재 cart 요약을 chat 입력 맥락에 포함 (system 또는 input 프리픽스)
3. `astream_events`로 토큰 스트리밍(기존 로직 유지)
4. 스트림 종료 후 `get_actions()`로 모인 액션을 각각 `data:{"action":...}` 로 전송
   - (대안: `on_tool_end` 시점에 즉시 흘려보내기 — MVP는 종료 후 일괄로 단순화)
5. `data:{"done":true,"output":...}` 전송
- ⚠️ ContextVar는 async 태스크 경계에서 전파 주의 → 요청 핸들러와 같은 태스크에서 set/get 되도록 유지

**`backend/api/llm.py`** — `LLMRequest` 확장
```python
class CartLine(BaseModel):
    cart_id: float | int | None = None
    menu_id: int
    name: str | None = None
    item_type: str = "single"
    quantity: int = 1
    unit_price: float = 0
    exclusion: str = "없음"
    side: str | None = None
    drink: str | None = None

class LLMRequest(BaseModel):
    session_id: str
    input: str
    language: str | None = None
    screen: str | None = None        # 신규
    cart: list[CartLine] = []        # 신규
```

---

## 5. 프론트엔드 구현 계획

### 5.1 `ChatPanel.jsx`
- props 확장: `cart`, `screen`, `onAction`
- 스트림 요청 body에 `screen`, `cart`(필요한 필드만 추려서) 포함
- SSE 파싱에 분기 추가:
  ```js
  if (data.action) props.onAction?.(data.action)
  ```
- 토큰/`done`/커서 로직은 기존 유지

### 5.2 `App.jsx`
- cart 라인을 LLM 친화 형태로 변환하는 `cartForLLM` 메모이즈:
  ```js
  cart.map(c => ({ cart_id:c.cartId, menu_id:c.id, name:c.name,
    item_type:c.type, quantity:c.qty, unit_price:c.unitPrice,
    exclusion:c.exclusion, side:c.side, drink:c.drink }))
  ```
- `<ChatPanel cart={cartForLLM} screen={screen} onAction={handleVoiceAction} ... />`
- `handleVoiceAction(a)`:
  ```js
  switch (a.type) {
    case 'add_item':    addToCart(buildCartItem(a)); break
    case 'update_qty':  { const id = resolveCartId(a.match); if(id!=null) updateQty(id, a.quantity) } break
    case 'remove_item': { const id = resolveCartId(a.match); if(id!=null) updateQty(id, 0) } break
    case 'clear_cart':  clearCart(); break
    case 'navigate':    nav(a.screen); break
    case 'checkout':    nav('cart'); break   // MVP: 장바구니로만
    default: console.warn('[voice] unknown action', a)
  }
  ```
- `buildCartItem(a)`: `a.menu_id`로 `menuData`에서 메뉴를 찾아 가격/이미지/세트옵션을 채워 §1 스키마로 변환
  - 세트면 SET_SIDES/SET_DRINKS에서 `a.side`/`a.drink` 매칭(없으면 기본값), unitPrice 공식 적용
  - `exclusion` 유효성: `menuData.exclusions`에 없는 값이면 '없음'으로 폴백 + special_note로 회피(선택)
- `resolveCartId(match)`: §2 match 규칙대로 현재 `cart`에서 cartId 탐색
- `special_note`: MVP에서는 cart 아이템에 필드 추가해 보관(표시는 선택). DB 미연결이므로 화면 메모로만.

### 5.3 화면 반영
- `addToCart`/`updateQty`/`nav`는 기존 함수 → 호출 즉시 React 리렌더로 화면 갱신
- 음성 답변은 기존대로 TTS 재생

---

## 6. 복합 발화 처리 예시 (동작 시나리오)

**"불고기버거 두 개랑 콜라 하나 주고, 버거는 양상추 빼줘. 결제할게"**
```jsonc
[ {"type":"add_item","menu_id":2,"item_type":"single","quantity":2,"exclusion":"양상추 제외"},
  {"type":"add_item","menu_id":17,"item_type":"single","quantity":1},
  {"type":"checkout"} ]
```
→ 화면: 장바구니에 2줄 추가 후 cart 화면 진입. TTS: "불고기버거 둘(양상추 빼고), 콜라 하나 담았어요. 총 11,000원입니다."

**"콜라는 사이다로 바꿔줘"**
```jsonc
[ {"type":"remove_item","match":{"menu_id":17}},
  {"type":"add_item","menu_id":19,"item_type":"single","quantity":1} ]
```

**"치즈버거 세트로 하나, 사이다로"**
```jsonc
[ {"type":"add_item","menu_id":5,"item_type":"set","quantity":1,"drink":"사이다"} ]
```
→ unitPrice = 4200 + 2000 + (0+0) = 6200

---

## 7. 안전장치 / 엣지 케이스 (MVP)

| 상황 | 처리 |
|------|------|
| 빈 장바구니에 결제 | LLM이 `checkout` 대신 "담긴 메뉴가 없어요" 안내 |
| 모호한 메뉴 | 되묻기, 액션 미발행 |
| 카탈로그에 없는 메뉴 | 추가 거부 + 유사 메뉴 제안 |
| 옵션 불일치(없는 exclusion) | '없음' 폴백 또는 special_note로 처리 |
| 답변-액션 불일치 | 프롬프트로 "호출한 도구와 답변을 일치"시키도록 강제 |
| 세트 옵션 누락 | 기본값(감자튀김/콜라) 자동 적용 |
| 세션/언어 리셋 | 기존 `kiosk-session-reset` 이벤트와 연동(대기화면 복귀 시 초기화) |

---

## 8. 구현 순서 (체크리스트)

### Step 1 — 백엔드 골격
- [ ] `menu_catalog.py` (menuData 미러 + 프롬프트 렌더)
- [ ] `action_context.py` (cart/actions ContextVar)
- [ ] `action_tools.py` (6개 도구, 액션 push)

### Step 2 — 에이전트 전환
- [ ] `prompts.py` 개정(카탈로그·장바구니 주입, 복합 발화 규칙)
- [ ] `agent.py`가 `ACTION_TOOLS` 사용
- [ ] `llm_service.run_agent_stream`이 cart 수용 + 액션 SSE 발행
- [ ] `api/llm.py` `LLMRequest`에 `cart`, `screen`

### Step 3 — 프론트 연결
- [ ] `ChatPanel`: cart/screen 전송 + action 파싱 → `onAction`
- [ ] `App`: `cartForLLM`, `handleVoiceAction`, `buildCartItem`, `resolveCartId`

### Step 4 — 검증
- [ ] 담기 1건 → 화면 반영
- [ ] 복합 발화(추가 2종+옵션) → 순서대로 반영
- [ ] 수량 변경 / 삭제 / 비우기
- [ ] "결제할게" → cart 화면 진입 + 총액 복창
- [ ] 세트 주문 가격 정확성
- [ ] 빈 장바구니 결제 가드

---

## 9. 의도적으로 MVP에서 제외 (차후)

- DB 영속화(ORDER/ORDER_ITEMS/PAYMENT, 주방 special_note 전달) → Phase 5
- RAG/FAISS 메뉴 검색(메뉴 대량화 시 재도입)
- `checkout`에서 결제수단까지 자동 진행(오결제 리스크 검토 후)
- 메뉴 카탈로그 단일 JSON 일원화(현재는 menuData.js ↔ menu_catalog.py 수동 동기화)

---

## 부록. 변경 파일 요약

| 구분 | 파일 | 작업 |
|------|------|------|
| 백엔드 신규 | `ai_modules/llm/menu_catalog.py` | 메뉴 카탈로그 + 프롬프트 렌더 |
| 백엔드 신규 | `ai_modules/llm/action_context.py` | cart/actions ContextVar |
| 백엔드 신규 | `ai_modules/llm/action_tools.py` | 6개 액션 도구 |
| 백엔드 수정 | `ai_modules/llm/agent.py` | 액션 도구·카탈로그 적용 |
| 백엔드 수정 | `ai_modules/llm/prompts.py` | 프롬프트 개정 |
| 백엔드 수정 | `backend/core/llm_service.py` | cart 수용 + 액션 SSE |
| 백엔드 수정 | `backend/api/llm.py` | `LLMRequest` 확장 |
| 프론트 수정 | `frontend/src/components/ChatPanel.jsx` | cart/screen 전송 + action 파싱 |
| 프론트 수정 | `frontend/src/App.jsx` | 액션 핸들러 + cart 변환 |
| 보존(미사용) | `ai_modules/llm/tools.py` | Phase 5에서 복원 |
