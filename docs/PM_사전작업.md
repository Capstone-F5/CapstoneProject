# PM 사전 작업 명세

> 팀장이 DB 파트·AI 파트 작업 착수 **전**에 완료해야 하는 항목들.  
> 두 파트의 작업 접점이 여기서 정의되므로, 이 문서가 확정되어야 각 담당자가 독립적으로 진행할 수 있다.

---

## 1. 현황 파악 (이미 완성된 것)

착수 전에 반드시 확인할 것. 아래는 **새로 만들 필요 없음**.

| 파일 | 상태 | 내용 |
|---|---|---|
| `backend/core/models.py` | ✅ 완성 | ORM 13개 테이블 전부 정의됨 |
| `backend/core/seed.py` | ✅ 완성 | PDF 메뉴 데이터(버거 13종, 사이드 6종, 음료 7종, 옵션) 전부 포함 |
| `backend/core/db.py` | ✅ 완성 | async SQLAlchemy 세션 팩토리, `init_db()` 포함 |
| `frontend/src/services/menuService.js` | ✅ 준비됨 | `VITE_API_URL` 환경변수 세팅 시 자동으로 API 호출로 전환 |
| `frontend/src/services/orderService.js` | ✅ 준비됨 | 동일 패턴, API 분기 이미 구현 |
| `ai_modules/llm/action_tools.py` | ⚠️ 수정 필요 | Tool 로직은 완성, 정적 카탈로그 의존성만 교체 필요 |

---

## 2. PM 직접 처리 항목

### 2-1. 환경변수 파일 정비

`.env.example`을 아래 내용으로 업데이트한 뒤 팀 전체에 공유한다.  
(실제 `.env`는 git에 올리지 않음)

```env
# OpenAI
OPENAI_API_KEY=
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_STT_MODEL=whisper-1
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=alloy

# Database
DATABASE_URL=sqlite+aiosqlite:///./kiosk.db

# Server
HOST=0.0.0.0
PORT=8000

# Frontend → Backend 연결 (프론트 .env에 추가)
# 이 값이 있어야 정적 데이터 대신 실제 API를 호출함
VITE_API_URL=http://localhost:8000
```

**프론트 `.env` 파일 위치:** `frontend/.env`  
(Vite는 `frontend/` 디렉토리에서 실행되므로 루트 `.env`와 별개)

---

### 2-2. Git 브랜치 전략 결정 및 공지

두 파트가 같은 파일을 동시에 수정하면 충돌이 발생한다.  
아래 브랜치 전략을 팀에 공지한다.

```
main
 ├── feature/db-api-server     ← DB 파트 담당자
 └── feature/llm-db-tools      ← AI 파트 담당자 (DB API가 올라온 후 시작)
```

**머지 순서:** `feature/db-api-server` → main → `feature/llm-db-tools` 시작

**충돌 예방 파일 분리:**
- DB 파트: `backend/dao/`, `backend/schemas/`, `backend/api/menu.py`, `cart.py`, `order.py`, `payment.py`, `user.py`, `backend/main.py`
- AI 파트: `ai_modules/llm/action_tools.py`, `ai_modules/llm/rag.py`, `ai_modules/llm/prompts.py`
- **공유 파일 없음** — 의도적으로 설계됨

---

### 2-3. API 인터페이스 계약 확정

아래 스펙은 프론트엔드 서비스 파일(`menuService.js`, `orderService.js`)이 이미 기대하는 형식이다.  
DB 파트 담당자가 **이 스펙 그대로** 구현해야 프론트 수정 없이 연동된다.

#### `GET /api/menu?locale=ko`

```json
{
  "categories": [
    { "id": "uuid", "name": "버거", "emoji": "🍔" }
  ],
  "menuItems": {
    "burger": [
      {
        "id": "uuid",
        "name": "F버거",
        "desc": "치킨과 불고기의 만남...",
        "price": 7500,
        "kcal": 820,
        "hasSet": true,
        "exclusions": ["양상추 제외", "양파 제외"],
        "image": "/images/burgers/F버거.webp",
        "setImage": "/images/sets/F버거 세트.webp"
      }
    ]
  },
  "setSides": [{ "name": "감자튀김", "extra": 0, "image": "..." }],
  "setDrinks": [{ "name": "콜라", "extra": 0, "image": "..." }],
  "setSurcharge": 2000
}
```

#### `POST /api/orders`

```json
// Request
{ "items": [...], "total": 15000, "orderType": "EAT_IN", "phone": "01012345678" }

// Response
{ "orderNum": 102, "orderId": "uuid" }
```

#### `POST /api/cart/{session_id}/items` (AI Tool용)

```json
// Request
{
  "menu_item_id": "uuid",
  "quantity": 1,
  "selected_options": [{"option_id": "uuid", "name": "양상추 제외"}],
  "special_note": "소스 따로 주세요"
}

// Response
{ "cart_item_id": "uuid", "cart_id": "uuid" }
```

#### `GET /api/cart/{session_id}`

```json
{
  "cart_id": "uuid",
  "session_id": "abc123",
  "items": [
    {
      "cart_item_id": "uuid",
      "menu_item_id": "uuid",
      "name_ko": "F버거",
      "quantity": 2,
      "unit_price": 7500,
      "selected_options": [],
      "special_note": null
    }
  ],
  "total": 15000
}
```

---

### 2-4. session_id 공유 방식 결정

현재 LLM 엔드포인트(`backend/api/llm.py`)는 이미 `session_id`를 받는다.  
이 `session_id`를 장바구니 식별자로 **그대로 재사용**하도록 결정한다.

**흐름:**
```
프론트엔드
  → STT 완료 후 session_id + text → POST /ai_modules/llm/stream
  → LLM이 add_to_cart Tool 호출 시 → POST /api/cart/{session_id}/items
  → 결제 시 → GET /api/cart/{session_id} → POST /api/orders
```

**session_id 생성 위치:** 프론트엔드에서 키오스크 세션 시작 시 `uuid()` 생성, localStorage에 저장.  
(현재 `action_context.py`의 세션 관리와 동일한 방식)

---

### 2-5. main.py 라우터 등록 준비

DB 파트 담당자가 API 파일을 만들면 `backend/main.py`에 라우터를 등록해야 한다.  
아래 코드 블록을 `main.py`에 추가할 위치를 미리 안내한다.

```python
# backend/main.py 에 추가할 내용 (DB 파트 완료 후)
from api.menu import router as menu_router
from api.cart import router as cart_router
from api.order import router as order_router
from api.payment import router as payment_router
from api.user import router as user_router

app.include_router(menu_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(user_router)
```

---

### 2-6. 폴더 생성

두 담당자 착수 전에 PM이 빈 폴더 및 `__init__.py`를 미리 만들어둔다.

```
backend/dao/__init__.py
backend/schemas/__init__.py
```

PowerShell에서:
```powershell
New-Item -ItemType Directory -Force backend/dao
New-Item -ItemType File backend/dao/__init__.py
New-Item -ItemType Directory -Force backend/schemas
New-Item -ItemType File backend/schemas/__init__.py
```

---

## 3. 작업 순서 (타임라인)

```
Week 1
  [PM]       2-1 ~ 2-6 완료, 각 담당자에게 명세서 전달
  [DB 파트]  schemas/ → dao/ → api/ → main.py 등록 → 동작 확인

Week 2
  [DB 파트]  /api/menu GET 완성 → 프론트 VITE_API_URL 설정 후 메뉴 화면 테스트
  [AI 파트]  DB API 로컬 서버 확인 후 action_tools.py 수정 시작

Week 3
  [AI 파트]  모든 Tool 교체 완료 → 음성 주문 E2E 테스트
  [PM]       feature/db-api-server → main 머지 → feature/llm-db-tools → main 머지
```

---

## 4. 통합 완료 기준 (PM 검수 체크리스트)

- [ ] `VITE_API_URL` 설정 시 프론트 메뉴 화면이 DB 데이터로 표시된다
- [ ] "F버거 세트 하나 주세요" 음성 입력 → 장바구니에 DB cart_item이 생성된다
- [ ] "양파 빼주세요" 음성 입력 → 해당 cart_item의 selected_options에 반영된다
- [ ] 결제 완료 → orders 테이블에 order 레코드가 생성된다
- [ ] "인기 메뉴 추천해줘" → DB is_popular=true 메뉴가 응답에 포함된다
- [ ] 비회원 주문이 session_id만으로 완료된다 (phone_number 불필요)
