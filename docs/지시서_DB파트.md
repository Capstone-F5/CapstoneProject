# 작업 지시서 — DB 파트 (서유민)

> **브랜치:** `feature/db-api-server`  
> **참고 문서:** `docs/DB_파트_작업명세.md` — 각 파일의 전체 코드가 여기 있음  
> **착수 조건:** PM에게 브랜치 링크 받은 후 시작

---

## 시작 전 확인

- [ ] `git checkout feature/db-api-server` 로 브랜치 전환
- [ ] `backend/dao/__init__.py`, `backend/schemas/__init__.py` 파일 존재 확인 (PM이 생성)
- [ ] `backend/core/models.py`, `backend/core/seed.py` — **수정하지 말 것**, 이미 완성됨

---

## Day 1 — schemas/ (DTO 작성)

> 명세서 코드를 보고 아래 파일을 순서대로 만든다.

- [ ] `backend/schemas/menu_schemas.py` 생성
  - `MenuOptionOut`, `MenuItemOut`, `CategoryOut`, `MenuResponse` 클래스
- [ ] `backend/schemas/cart_schemas.py` 생성
  - `SelectedOption`, `CartItemIn`, `CartItemOut`, `CartItemUpdateIn`, `CartOut` 클래스
- [ ] `backend/schemas/order_schemas.py` 생성
  - `OrderIn`, `OrderItemOut`, `OrderOut` 클래스
- [ ] `backend/schemas/payment_schemas.py` 생성
  - `PaymentIn`, `PaymentOut` 클래스
- [ ] `backend/schemas/user_schemas.py` 생성
  - `UserPointsOut`, `CouponOut` 클래스

**Day 1 완료 확인:** `python -c "from schemas.menu_schemas import MenuResponse; print('OK')"` 에러 없음

---

## Day 2 — dao/ (DB 접근 계층)

- [ ] `backend/dao/menu_dao.py` 생성
  - `get_all_categories()`, `get_menu_items_by_category()`, `get_menu_item_by_id()`, `get_popular_items()`
- [ ] `backend/dao/cart_dao.py` 생성
  - `get_or_create_cart()`, `get_cart_with_items()`, `add_cart_item()`, `update_cart_item()`, `delete_cart_item()`, `clear_cart()`
- [ ] `backend/dao/order_dao.py` 생성
  - `create_order_from_cart()`, `create_order_items_from_cart_items()`, `get_order_by_id()`
- [ ] `backend/dao/payment_dao.py` 생성
  - `create_payment()`
- [ ] `backend/dao/user_dao.py` 생성
  - `get_user_by_phone()`, `get_membership()`, `get_unused_coupons()`, `get_coupon_by_code()`

**주의사항:**
- 모든 함수는 `async def`
- `await db.commit()`은 DAO 내부에서 절대 호출하지 않음 (라우터에서만 커밋)

---

## Day 3 — api/ (FastAPI 엔드포인트)

- [ ] `backend/api/menu.py` 생성
  - `GET /api/menu` (locale 파라미터 지원)
  - `GET /api/menu/items/{item_id}`
- [ ] `backend/api/cart.py` 생성
  - `GET /api/cart/{session_id}`
  - `POST /api/cart/{session_id}/items`
  - `PATCH /api/cart/{session_id}/items/{cart_item_id}`
  - `DELETE /api/cart/{session_id}/items/{cart_item_id}`
  - `DELETE /api/cart/{session_id}` (전체 비우기)
- [ ] `backend/api/order.py` 생성
  - `POST /api/orders`
  - `GET /api/orders/{order_id}`
- [ ] `backend/api/payment.py` 생성
  - `POST /api/payments`
- [ ] `backend/api/user.py` 생성
  - `GET /api/user/points/{phone}`
  - `GET /api/user/{user_id}/coupons`

---

## Day 4 — 등록 및 동작 테스트

- [ ] `backend/main.py` 열기 — 기존 라우터 등록 코드 아래에 아래 5줄 추가
  ```python
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
- [ ] 서버 기동: `cd backend && uvicorn main:app --reload`
- [ ] 브라우저에서 `http://localhost:8000/docs` 열어 전 엔드포인트 스웨거 확인
- [ ] `GET http://localhost:8000/api/menu` — JSON 응답 확인
- [ ] `POST http://localhost:8000/api/cart/test-session/items` — 장바구니 추가 테스트
- [ ] `GET http://localhost:8000/api/cart/test-session` — 추가된 항목 확인

---

## 완료 보고

아래 4가지 캡처 또는 로그를 PM(조예성)에게 전달:

1. `/docs` 스웨거 화면 캡처
2. `GET /api/menu` 응답 JSON
3. 장바구니 추가 → 조회 결과
4. `POST /api/orders` 응답 (order_number 포함)

> 보고 받은 PM이 프론트 연동 테스트 후 main 머지 진행
