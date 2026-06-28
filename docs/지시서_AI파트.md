# 작업 지시서 — AI Tool 파트 (김성원·임지연)

> **브랜치:** `feature/llm-db-tools`  
> **참고 문서:** `docs/AI_파트_작업명세.md` — 각 파일의 전체 코드가 여기 있음  
> **착수 조건:** PM으로부터 "DB 파트 main 머지 완료" 신호를 받은 후 시작  
> **역할 분배:** 김성원 — `action_tools.py` 재작성 / 임지연 — `api_client.py`, `rag.py`, `prompts.py`

---

## 시작 전 확인 (둘 다)

- [ ] `git checkout feature/llm-db-tools` 브랜치 전환
- [ ] 로컬에서 백엔드 서버 기동 확인: `GET http://localhost:8000/api/menu` 응답 오는지 테스트
- [ ] `backend/core/.env`에 `API_BASE_URL=http://localhost:8000` 있는지 확인

---

## 임지연 담당

### Step 1. `api_client.py` 생성

`ai_modules/llm/api_client.py` 신규 생성

만들어야 할 함수 (명세서 참고):
- [ ] `fetch_menu_items()` — `GET /api/menu` → items 평탄화 반환
- [ ] `fetch_menu_item_by_id(item_id)` — `GET /api/menu/items/{id}`
- [ ] `post_cart_add(session_id, payload)` — `POST /api/cart/{session_id}/items`
- [ ] `patch_cart_item(session_id, cart_item_id, payload)` — `PATCH /api/cart/.../items/...`
- [ ] `delete_cart_item(session_id, cart_item_id)` — `DELETE /api/cart/.../items/...`
- [ ] `delete_cart(session_id)` — `DELETE /api/cart/{session_id}`
- [ ] `get_cart(session_id)` — `GET /api/cart/{session_id}`
- [ ] `get_user_points(phone)` — `GET /api/user/points/{phone}`

완료 확인: `python -c "from ai_modules.llm.api_client import fetch_menu_items; print('OK')`

### Step 2. `action_context.py`에 session_id 관리 추가

`ai_modules/llm/action_context.py` 열기 → 파일 맨 아래에 추가:

```python
_session_id: str = "default"

def set_session_id(sid: str) -> None:
    global _session_id
    _session_id = sid

def get_session_id() -> str:
    return _session_id
```

### Step 3. `backend/api/llm.py` 수정

`llm.py`에서 agent 실행 직전에 아래 한 줄 추가:

```python
from ai_modules.llm.action_context import set_session_id
set_session_id(session_id)   # 요청에서 받은 session_id 주입
```

`session_id`가 어디서 오는지는 기존 `llm.py` 코드 확인 후 적절한 위치에 삽입.

### Step 4. `rag.py` 개선

기존 `ai_modules/llm/rag.py` 열기 → 명세서의 `build_menu_index()`, `search_menu_by_query()` 함수 추가

### Step 5. `prompts.py` 보완

기존 `ai_modules/llm/prompts.py` 열기 → 명세서의 `ADDITIONAL_SCENARIOS` 내용을 시스템 프롬프트 문자열에 이어붙이기

---

## 김성원 담당

### Step 1. `action_tools.py` 전체 재작성

> 임지연의 `api_client.py`가 먼저 완성되어야 함. 완성 확인 후 진행.

**변경 전 동작 확인 (백업 개념):**
- [ ] 현재 `action_tools.py`를 `action_tools_legacy.py`로 복사해두기

**재작성 순서:**

- [ ] 파일 상단 import 교체
  ```python
  # 제거: from .menu_catalog import ...
  # 추가: from . import api_client
  # 추가: from .action_context import get_session_id
  ```

- [ ] `add_item` Tool 재작성
  - 파라미터: `menu_item_id: str` (기존 `menu_id: int` 교체)
  - `api_client.fetch_menu_item_by_id(menu_item_id)` 로 DB 조회 및 유효성 검증
  - `api_client.post_cart_add(session_id, payload)` 로 DB 저장
  - `push_action()` 으로 프론트 액션 큐 등록 (유지)

- [ ] `remove_item` Tool 재작성
  - 파라미터: `cart_item_id: str` (기존 `menu_id: int` 교체)
  - `api_client.delete_cart_item(session_id, cart_item_id)` 호출

- [ ] `update_item_options` Tool 재작성 (기존 `update_qty` + `update_item` 통합)
  - 파라미터: `cart_item_id: str`, `quantity`, `exclusions`, `special_note`
  - `api_client.patch_cart_item(session_id, cart_item_id, payload)` 호출

- [ ] `get_cart_status` Tool **신규 추가**
  - `api_client.get_cart(session_id)` 조회 후 사람이 읽는 문자열 반환
  - cart_item_id를 응답에 포함시켜 수정·삭제 시 사용 가능하게 함

- [ ] `check_user_points` Tool **신규 추가**
  - `api_client.get_user_points(phone)` 호출

- [ ] `clear_cart` Tool 수정
  - `api_client.delete_cart(session_id)` 호출

- [ ] `navigate`, `checkout`, `ui_action` — **수정 없이 그대로 유지**

- [ ] 파일 맨 아래 `ACTION_TOOLS` 리스트 업데이트
  ```python
  ACTION_TOOLS = [
      add_item, remove_item, update_item_options,
      get_cart_status, clear_cart, check_user_points,
      navigate, checkout, ui_action,
  ]
  ```

### Step 2. `menu_catalog.py` 주석 추가

`ai_modules/llm/menu_catalog.py` 열기 → 파일 맨 위에 추가:

```python
# ⚠️ 이 파일은 STT 어휘 힌트 전용으로 역할이 축소됨.
# action_tools.py 에서 MENU_CATALOG, get_menu() 는 더 이상 import하지 않음.
```

기존 `action_tools.py`에서 `from .menu_catalog import ...` import 줄이 모두 제거되었는지 확인.

---

## 공통 — 통합 테스트

둘 다 준비되면 함께 테스트:

- [ ] 백엔드 서버 기동
- [ ] 음성 or 텍스트로 "F버거 세트 하나 주세요" 전송
  - `GET /api/cart/{session_id}` 에서 cart_item 생성 확인
- [ ] "양파 빼주세요" 전송
  - selected_options에 "양파 제외" 포함 확인
- [ ] "장바구니 보여줘" 전송
  - LLM이 get_cart_status Tool을 호출해 실데이터 반환하는지 확인
- [ ] "비건 버거 있어?" 전송
  - RAG 또는 description 기반 추천 응답 확인
- [ ] 없는 메뉴 ID 사용 시도 → "찾을 수 없습니다" 에러 메시지 확인

---

## 완료 보고

PM(조예성)에게 전달:

1. "F버거 세트 하나 주세요" 실행 후 `GET /api/cart/{session_id}` 응답 JSON
2. `action_tools.py` 상단에 `from .menu_catalog import` 가 없는 것 확인 (스크린샷 or diff)
3. 통합 테스트 6항목 체크리스트 통과 여부

---

## 주의사항

- `_run()` 헬퍼 함수: LangChain Tool은 동기 함수지만 내부에서 async API를 호출해야 하므로 명세서의 `_run()` 패턴 반드시 사용
- `session_id`는 Tool 내부에서 `get_session_id()` 로 가져옴 — Tool 파라미터로 받지 않음
- `push_action()`은 제거하지 말 것 — 프론트 실시간 반영에 여전히 필요
