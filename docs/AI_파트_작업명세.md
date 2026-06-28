# AI Tool 파트 작업 명세

> **담당자:** 김성원, 임지연  
> **브랜치:** `feature/llm-db-tools`  
> **목표:** LLM Agent가 정적 카탈로그 대신 실제 DB API를 통해 메뉴 조회·장바구니 조작을 수행하도록 교체  
> **선행 조건:** `feature/db-api-server` 브랜치가 main에 머지되어 `/api/cart`, `/api/menu` 등이 동작해야 착수 가능

---

## 이미 완성된 것 (건드리지 말 것)

| 파일 | 유지 이유 |
|---|---|
| `ai_modules/llm/agent.py` | LangChain agent 구성, `ACTION_TOOLS` import 구조 그대로 유지 |
| `ai_modules/llm/action_context.py` | `push_action()`, `get_cart()` — 프론트 액션 큐 관리, 건드리지 않음 |
| `ai_modules/llm/memory.py` | `ConversationSummaryBufferMemory` — 유지 |
| `ai_modules/llm/session_context.py` | 세션 관리 — 유지 |
| `backend/api/llm.py` | LLM 엔드포인트 — 유지 (session_id 전달 구조 이미 있음) |

---

## 수정할 파일 목록

```
ai_modules/llm/
  action_tools.py       ← 핵심 수정 (DB API 호출로 교체)
  prompts.py            ← 보완 (쿠폰·포인트 안내 시나리오 추가)
  rag.py                ← 개선 (DB description 필드 기반 인덱싱)
  menu_catalog.py       ← 역할 축소 (STT 어휘힌트 전용, 카탈로그 룩업 제거)
```

---

## 구현 명세

### 핵심 아키텍처 변경

**Before:** LLM Tool → `menu_catalog.py` (정적 dict) → `action_context.py` (인메모리 큐)  
**After:** LLM Tool → `httpx` → FastAPI `/api/*` (DB) + `action_context.py` (인메모리 큐 유지)

> 중요: `push_action()`과 프론트엔드로 가는 액션 큐는 **그대로 유지**한다.  
> DB API는 Tool이 검증·조작하는 용도이고, 프론트엔드 상태 반영은 여전히 action 큐를 통한다.

---

### 1단계: API 클라이언트 유틸리티 추가

`ai_modules/llm/api_client.py` 신규 생성

```python
"""
DB API 호출 유틸리티.
action_tools.py 에서 httpx 로 내부 API를 호출할 때 사용.
"""
import os
import httpx

_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

async def fetch_menu_items() -> list[dict]:
    """GET /api/menu → items 목록 반환."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{_BASE}/api/menu?locale=ko")
        res.raise_for_status()
        data = res.json()
    # 카테고리별로 분산된 items를 평탄화
    items = []
    for category_items in data.get("menu_items", {}).values():
        items.extend(category_items)
    return items

async def fetch_menu_item_by_id(item_id: str) -> dict | None:
    """GET /api/menu/items/{id}"""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{_BASE}/api/menu/items/{item_id}")
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()

async def post_cart_add(session_id: str, payload: dict) -> dict:
    """POST /api/cart/{session_id}/items"""
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{_BASE}/api/cart/{session_id}/items", json=payload)
        res.raise_for_status()
        return res.json()

async def patch_cart_item(session_id: str, cart_item_id: str, payload: dict) -> None:
    """PATCH /api/cart/{session_id}/items/{cart_item_id}"""
    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"{_BASE}/api/cart/{session_id}/items/{cart_item_id}", json=payload
        )
        res.raise_for_status()

async def delete_cart_item(session_id: str, cart_item_id: str) -> None:
    """DELETE /api/cart/{session_id}/items/{cart_item_id}"""
    async with httpx.AsyncClient() as client:
        res = await client.delete(f"{_BASE}/api/cart/{session_id}/items/{cart_item_id}")
        res.raise_for_status()

async def delete_cart(session_id: str) -> None:
    """DELETE /api/cart/{session_id} (전체 비우기)"""
    async with httpx.AsyncClient() as client:
        res = await client.delete(f"{_BASE}/api/cart/{session_id}")
        res.raise_for_status()

async def get_cart(session_id: str) -> dict:
    """GET /api/cart/{session_id}"""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{_BASE}/api/cart/{session_id}")
        res.raise_for_status()
        return res.json()

async def get_user_points(phone: str) -> dict | None:
    """GET /api/user/points/{phone}"""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{_BASE}/api/user/points/{phone}")
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()
```

`.env.example`에 추가 필요:
```env
# AI 모듈 → 백엔드 API URL (로컬 개발 시 동일 서버)
API_BASE_URL=http://localhost:8000
```

---

### 2단계: action_tools.py 수정

**변경 원칙:**
- `menu_catalog.py`의 `get_menu(id)` 룩업 → DB API 조회로 교체
- `menu_id` 타입을 정수 → 문자열 UUID로 변경 (DB의 PK가 uuid)
- `session_id`는 `action_context.py`의 `get_session_id()` 함수로 주입 받음
- Tool 로직은 유지, 검증 방식만 변경

#### `action_context.py`에 session_id getter 추가 필요

`ai_modules/llm/action_context.py`에 다음을 추가한다.

```python
_session_id: str = "default"

def set_session_id(sid: str) -> None:
    global _session_id
    _session_id = sid

def get_session_id() -> str:
    return _session_id
```

LLM 엔드포인트(`backend/api/llm.py`)에서 agent 실행 전에 `set_session_id(session_id)` 호출.

---

#### `action_tools.py` 전체 재작성 내용

```python
"""
음성 주문 액션 도구 — DB API 연동.

각 Tool은:
  1. DB API로 메뉴/장바구니 검증
  2. DB 반영 (POST/PATCH/DELETE /api/cart/...)
  3. push_action()으로 프론트엔드 액션 큐에 등록
  4. 사람이 읽을 확인 문자열 반환
"""
from __future__ import annotations
import asyncio
from langchain_core.tools import tool
from .action_context import get_cart as get_cart_context, push_action, get_session_id
from . import api_client


def _run(coro):
    """LangChain 동기 tool에서 async 호출용 헬퍼."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except Exception:
        return asyncio.run(coro)


@tool
def add_item(
    menu_item_id: str,
    quantity: int = 1,
    upgrade_to_set: bool = False,
    exclusions: list[str] | None = None,
    special_note: str | None = None,
) -> str:
    """장바구니에 메뉴를 담는다.

    Args:
        menu_item_id: DB의 메뉴 UUID. 메뉴 목록에서 확인할 것.
        quantity: 담을 수량 (1 이상).
        upgrade_to_set: True이면 세트 업그레이드 옵션 자동 추가.
        exclusions: 제외할 재료 이름 목록. 예: ["양파", "양상추"]
        special_note: 주방 전달 비정형 요구사항. 예: "반으로 잘라주세요"
    """
    session_id = get_session_id()

    try:
        item = _run(api_client.fetch_menu_item_by_id(menu_item_id))
    except Exception as e:
        return f"오류: 메뉴 조회 실패 — {e}"

    if item is None:
        return f"오류: 해당 ID의 메뉴를 찾을 수 없습니다 ({menu_item_id})"

    if not item.get("is_available", True):
        return f"죄송합니다, {item['name_ko']}는 현재 품절입니다."

    # 옵션 구성
    selected_options = []
    options = item.get("options", [])

    if upgrade_to_set:
        set_opt = next((o for o in options if "세트" in o["name_ko"]), None)
        if set_opt:
            selected_options.append({"option_id": set_opt["id"], "name": set_opt["name_ko"]})
        else:
            return f"오류: {item['name_ko']}는 세트 주문이 불가합니다."

    for excl in (exclusions or []):
        opt = next(
            (o for o in options if excl in o["name_ko"] and o.get("is_available", True)),
            None
        )
        if opt:
            selected_options.append({"option_id": opt["id"], "name": opt["name_ko"]})

    payload = {
        "menu_item_id": menu_item_id,
        "quantity": quantity,
        "selected_options": selected_options,
        "special_note": special_note,
    }

    try:
        result = _run(api_client.post_cart_add(session_id, payload))
    except Exception as e:
        return f"오류: 장바구니 추가 실패 — {e}"

    cart_item_id = result.get("cart_item_id")

    # 프론트엔드 액션 큐
    push_action({
        "type": "add_item",
        "menu_item_id": menu_item_id,
        "name": item["name_ko"],
        "quantity": quantity,
        "upgrade_to_set": upgrade_to_set,
        "exclusions": exclusions or [],
        "cart_item_id": cart_item_id,
    })

    type_label = "세트" if upgrade_to_set else "단품"
    msg = f"{item['name_ko']}({type_label}) {quantity}개 담음"
    if exclusions:
        msg += f" [{', '.join(exclusions)} 제외]"
    if special_note:
        msg += f" [특이사항: {special_note}]"
    return msg


@tool
def remove_item(cart_item_id: str) -> str:
    """장바구니에서 특정 항목을 삭제한다.

    Args:
        cart_item_id: 삭제할 장바구니 항목의 ID. get_cart_status로 확인 가능.
    """
    session_id = get_session_id()
    try:
        _run(api_client.delete_cart_item(session_id, cart_item_id))
    except Exception as e:
        return f"오류: 삭제 실패 — {e}"

    push_action({"type": "remove_item", "cart_item_id": cart_item_id})
    return "항목을 장바구니에서 삭제했습니다."


@tool
def update_item_options(
    cart_item_id: str,
    quantity: int | None = None,
    exclusions: list[str] | None = None,
    special_note: str | None = None,
) -> str:
    """장바구니 항목의 수량 또는 옵션을 변경한다.

    Args:
        cart_item_id: 변경할 장바구니 항목 ID.
        quantity: 새 수량.
        exclusions: 새 제외 옵션 목록.
        special_note: 새 특이사항.
    """
    session_id = get_session_id()
    payload: dict = {}
    if quantity is not None:
        payload["quantity"] = quantity
    if special_note is not None:
        payload["special_note"] = special_note

    try:
        _run(api_client.patch_cart_item(session_id, cart_item_id, payload))
    except Exception as e:
        return f"오류: 수정 실패 — {e}"

    push_action({"type": "update_item", "cart_item_id": cart_item_id, **payload})
    return "장바구니 항목을 수정했습니다."


@tool
def get_cart_status() -> str:
    """현재 장바구니 내용을 조회한다. 항목 수정·삭제 전에 cart_item_id 확인용으로 사용."""
    session_id = get_session_id()
    try:
        cart = _run(api_client.get_cart(session_id))
    except Exception as e:
        return f"오류: 장바구니 조회 실패 — {e}"

    items = cart.get("items", [])
    if not items:
        return "장바구니가 비어있습니다."

    lines = ["[현재 장바구니]"]
    for item in items:
        opts = ", ".join(o["name"] for o in item.get("selected_options", []))
        line = f"- {item['name_ko']} x{item['quantity']} ({int(item['unit_price'])}원)"
        if opts:
            line += f" [{opts}]"
        if item.get("special_note"):
            line += f" [{item['special_note']}]"
        line += f" (cart_item_id: {item['cart_item_id']})"
        lines.append(line)
    lines.append(f"합계: {int(cart.get('total', 0))}원")
    return "\n".join(lines)


@tool
def clear_cart() -> str:
    """장바구니를 전부 비운다."""
    session_id = get_session_id()
    try:
        _run(api_client.delete_cart(session_id))
    except Exception as e:
        return f"오류: 초기화 실패 — {e}"
    push_action({"type": "clear_cart"})
    return "장바구니를 비웠습니다."


@tool
def check_user_points(phone: str) -> str:
    """전화번호로 회원 포인트를 조회한다.

    Args:
        phone: 전화번호 (숫자만, 예: 01012345678)
    """
    try:
        data = _run(api_client.get_user_points(phone))
    except Exception as e:
        return f"오류: 포인트 조회 실패 — {e}"

    if data is None:
        return "등록된 회원 정보가 없습니다. 주문 후 포인트 적립이 가능합니다."

    return (
        f"안녕하세요! 현재 포인트는 {data['current_points']}점이며, "
        f"등급은 {data.get('tier', 'BASIC')}입니다."
    )


# 기존 navigate, checkout, ui_action 은 변경 없이 그대로 유지
from .action_context import push_action

@tool
def navigate(screen: str) -> str:
    """화면을 이동한다. Args: screen: 'menu' | 'cart' | 'payment'"""
    push_action({"type": "navigate", "screen": screen})
    return f"{screen} 화면으로 이동"


# (ui_action, checkout은 기존 코드 그대로 붙여넣기)
# action_tools.py 하단의 ACTION_TOOLS 리스트도 업데이트 필요

ACTION_TOOLS = [
    add_item,
    remove_item,
    update_item_options,
    get_cart_status,
    clear_cart,
    check_user_points,
    navigate,
    # checkout, ui_action — 기존 것 유지
]
```

---

### 3단계: prompts.py 보완

`ai_modules/llm/prompts.py`의 시스템 프롬프트에 아래 시나리오 안내를 추가한다.

```python
# prompts.py 에 추가할 섹션

ADDITIONAL_SCENARIOS = """
## 포인트·쿠폰 안내 시나리오
- 사용자가 전화번호를 말하면 check_user_points Tool을 호출해 포인트를 안내한다.
- 사용자가 포인트 사용을 원하면 결제 화면에서 ui_action(action='points', value='yes')을 호출한다.

## 메뉴 추천 시나리오
- '뭐가 맛있어요?', '인기 메뉴 뭐예요?' → is_popular=true 메뉴를 안내한다.
- '덜 매운 거', '비건이요' → RAG 검색 결과로 description 기반 추천한다.
- '저칼로리' → description에 낮은 kcal 값이 있는 메뉴 안내한다.

## 품절 처리
- add_item Tool이 '현재 품절' 메시지를 반환하면 대안 메뉴를 즉시 제안한다.
- 예: "F버거는 현재 품절입니다. 비슷한 더블 불고기 버거는 어떠세요?"

## 특이사항(special_note) 수집
- '빵 데워주세요', '소스 따로요', '반으로 잘라주세요' 같은 비정형 요청은
  add_item 또는 update_item_options의 special_note 파라미터로 전달한다.
- special_note는 주방에 그대로 전달되므로 정확히 요약해서 전달한다.

## 장바구니 수정
- '아까 담은 버거 빼주세요' → get_cart_status 먼저 호출해 cart_item_id 확인 후 remove_item.
- '수량 2개로 바꿔주세요' → get_cart_status → update_item_options.
"""
```

---

### 4단계: rag.py 개선

현재 `rag.py`는 비어있거나 미완성 상태일 수 있다. DB의 `description` 필드를 벡터 인덱싱하여 메뉴 추천 쿼리에 활용한다.

**구현 방향:**

```python
# ai_modules/llm/rag.py

import httpx
import os

_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

async def build_menu_index() -> list[dict]:
    """
    서버 시작 시 DB에서 메뉴 description을 가져와 인덱스 구성.
    ChromaDB 또는 간단한 키워드 매칭으로 구현 가능.
    """
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{_BASE}/api/menu?locale=ko")
        data = res.json()

    documents = []
    for items in data.get("menu_items", {}).values():
        for item in items:
            documents.append({
                "id": item["id"],
                "name": item["name_ko"],
                "description": item["desc"],
                "text": f"{item['name_ko']}: {item['desc']}",
            })
    return documents

def search_menu_by_query(query: str, documents: list[dict], top_k: int = 3) -> list[dict]:
    """
    간단한 키워드 매칭 버전 (1차 구현).
    이후 ChromaDB + 임베딩으로 업그레이드 가능.
    """
    query_lower = query.lower()
    scored = []
    for doc in documents:
        score = sum(1 for kw in query_lower.split() if kw in doc["text"])
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    return [doc for _, doc in scored[:top_k]]
```

---

### 5단계: menu_catalog.py 역할 축소

`menu_catalog.py`에서 Tool이 참조하던 `get_menu(id)`, `MENU_CATALOG` 등은 더 이상 사용하지 않는다.  
단, `render_vocab_for_stt()` 함수는 **Whisper STT 어휘힌트 용도**이므로 유지한다.

파일 상단에 주석 추가:
```python
# ⚠️ menu_catalog.py 는 STT 어휘 힌트 전용으로 역할이 축소됨.
# LLM Tool의 메뉴 조회는 DB API (api_client.py)를 통해 수행한다.
# MENU_CATALOG, get_menu() 는 레거시이며 action_tools.py에서 더 이상 import하지 않음.
```

---

## 완료 기준

- [ ] "F버거 세트 하나 주세요" → DB에 cart_item 생성 확인 (`GET /api/cart/{session_id}`)
- [ ] "양파 빼주세요" → selected_options에 "양파 제외" 옵션 포함 확인
- [ ] "장바구니 보여줘" → get_cart_status Tool이 DB 실데이터 반환
- [ ] "포인트 확인해줘, 010-1234-5678" → check_user_points 동작 (미등록 시 안내)
- [ ] "비건 버거 있어?" → RAG 또는 description 기반 추천 응답
- [ ] 품절 메뉴 추가 시도 → 친절한 대안 제안
- [ ] `menu_catalog.py`의 `MENU_CATALOG`을 `action_tools.py`에서 import하는 코드가 없음

---

## 참고: Tool 파라미터 타입 변경 요약

| Tool | Before | After |
|---|---|---|
| `add_item` | `menu_id: int` (카탈로그 숫자 ID) | `menu_item_id: str` (DB UUID) |
| `remove_item` | `menu_id: int` | `cart_item_id: str` (DB UUID) |
| `update_qty` | `menu_id: int, quantity: int` | `update_item_options` 통합 |
| `update_item` | `cart_id: float` (인메모리) | `cart_item_id: str` (DB UUID) |
| `get_cart_status` | 없음 (action_context 참조) | **신규** (DB API 조회) |
| `check_user_points` | 없음 | **신규** |

> **LLM 프롬프트 업데이트 필수:** Tool 파라미터가 바뀌었으므로 `prompts.py`의 메뉴 카탈로그 섹션도 "메뉴 ID는 숫자가 아닌 UUID" 로 안내해야 Agent가 올바른 ID를 사용한다.  
> 실용적인 방법: LLM 호출 시마다 `GET /api/menu` 결과를 프롬프트에 포함하거나, `get_cart_status` 처럼 메뉴 목록 조회 Tool을 추가한다.
