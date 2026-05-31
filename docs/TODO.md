# 음성 주문 제어 — TODO

> 작성일: 2026-05-30
> 관련: [voice-order-mvp-spec.md](voice-order-mvp-spec.md)

---

## 1. AI 참고용 매뉴얼 제작

LLM이 주문/조작 시 참고할 단일 기준 문서. 현재 프롬프트에 흩어진 정보(메뉴 카탈로그, 화면별 동작, 액션 프로토콜)를 한곳에 정리한다.

- [ ] **메뉴 카탈로그 정리** — 23개 메뉴 ID·이름·가격·세트가능·제외옵션 표 (`menu_catalog.py` ↔ `menuData.js` 동기화 기준)
- [ ] **세트 옵션 정리** — SET_SIDES / SET_DRINKS / SET_SURCHARGE, unitPrice 계산식
- [ ] **액션 프로토콜 정리** — `add_item`/`update_qty`/`remove_item`/`clear_cart`/`navigate`/`checkout` + `ui_action`(11종) 의 type·필드·예시
- [ ] **화면별 가능 동작 표** — start / orderType / menu / cart / complete 각 화면에서 호출 가능한 도구
- [ ] **발화 예시 모음** — 단건/복합/결제/부가기능 시나리오별 입력→액션 매핑 예시
- [ ] (검토) 이 매뉴얼을 프롬프트에 주입할지 / 개발자 참고용 문서로만 둘지 결정

## 2. UI 장바구니 ↔ AI 참조 장바구니 동기화

AI가 참조하는 장바구니와 UI에 표시되는 장바구니가 항상 같은 상태를 가리키도록 보장한다.

**현재 구조:**
- UI: `App.jsx`의 React `cart` state (단일 진실 공급원)
- AI 참조: `cartForLLM` (`cart` → LLM 친화 형태로 변환) → `ChatPanel`이 매 요청 body에 포함 → 백엔드 `set_cart()` → LLM 컨텍스트 주입

**이미 수정한 것:**
- [x] `ChatPanel`의 stale closure 수정 — `cartRef.current = cart`로 항상 최신값 전달
- [x] `buildCartItem`이 `useMenuData()` 소스 사용 — UI와 동일한 메뉴 데이터 기준

**남은 검증/작업:**
- [ ] 실제 동작 검증 — 음성으로 담은 항목이 UI에 반영되고, 다음 발화 시 AI가 그 항목을 인지하는지 확인
- [ ] 수동으로 담은 항목도 AI가 인지하는지 확인 (UI → cartForLLM → LLM 경로)
- [ ] `cartForLLM`과 실제 `cart` state 필드 매핑 정확성 점검 (`qty`↔`quantity`, `id`↔`menu_id` 등)

---

> 각 항목의 세부 범위는 논의 후 확정. 우선순위/담당 추가 예정.
