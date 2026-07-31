# DB 스키마 현황 (`kiosk_db`)

> 스냅샷 기준: 2026-07-24. MySQL 8.0 / `utf8mb4_unicode_ci`.
> 마이그레이션 도구(Alembic 등) 없음 — 앱 기동 시 `backend/core/db.py`의 `init_db()`가
> SQLAlchemy `Base.metadata.create_all()`로 **없는 테이블만** 생성하고, `backend/core/seed.py` /
> `admin_seed.py`의 시드 함수로 초기 데이터를 채운다. 이미 존재하는 테이블에 컬럼을 추가하는
> 등의 변경은 `create_all()`이 처리하지 못하므로 수동 `ALTER TABLE`이 필요하다(이번 세션에서
> 실제로 여러 번 수동 반영함 — `users.name`, `menu_options.option_group`,
> `menu_items.image_url/set_image_url`, `orders.status/user_coupon_id` 등).

## 목차

1. [회원 / 포인트](#1-회원--포인트) — `users`, `memberships`, `point_earn_logs`
2. [메뉴](#2-메뉴) — `categories`, `menu_items`, `menu_options`, `allergens`, `menu_item_allergens`
3. [장바구니](#3-장바구니) — `carts`, `cart_items`
4. [주문 / 결제](#4-주문--결제) — `orders`, `order_items`, `payments`
5. [쿠폰 / 할인](#5-쿠폰--할인) — `coupons`, `user_coupons`, `discounts`
6. [관리자](#6-관리자) — `admin_users`
7. [키오스크 설정](#7-키오스크-설정) — `start_screen_images`
8. [현재 데이터 스냅샷](#8-현재-데이터-스냅샷-행-수)

---

## 1. 회원 / 포인트

### `users`
비회원 주문도 지원하므로 `phone_number`/`name`은 모두 nullable. 전화번호로 포인트 적립을 요청하면
자동으로 이 테이블에 guest 계정이 생성된다(`backend/dao/user_dao.py:create_guest_user`).

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| phone_number | varchar(32) UNIQUE | YES | NULL | 없으면 완전 비회원 |
| name | varchar(64) | YES | NULL | 가입 플로우 자체가 없어 대부분 NULL. 프론트는 NULL이면 "이름없음님"으로 표시 |
| accessibility_mode | enum(NORMAL,VOICE_GUIDE,HIGH_CONTRAST,LARGE_TEXT) | NO | NORMAL | 현재 실제로 읽고 쓰는 API 로직 없음(스키마만 존재) |
| preferred_language | enum(ko,en,zh,ja) | NO | ko | |
| is_guest | tinyint(1) | NO | 1 | |
| current_points | int | NO | 0 | 실시간 잔액(적립/사용/만료 반영된 값) |
| created_at / updated_at | datetime | NO | now() | |

### `memberships`
`tier`(BASIC/SILVER/GOLD) 산정 로직은 아직 없음 — 테이블만 존재하고 현재 데이터 0건.
`GET /api/user/points/{phone}`가 `tier`를 조회하지만 매칭되는 행이 없으면 `null` 반환.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| user_id | varchar(36) FK→users.id | NO | | |
| tier | enum(BASIC,SILVER,GOLD) | NO | BASIC | |
| points | int | NO | 0 | `users.current_points`와 별개 필드(현재 동기화 로직 없음 — 사실상 미사용) |
| updated_at | datetime | NO | now() | |

### `point_earn_logs`
포인트 **적립 건별 원장**. 30일 경과 시 자동 만료 처리의 기준이 되는 테이블
(`backend/dao/user_dao.py: expire_old_points`, `consume_points_fifo`). 주문 생성 시 적립분만큼
한 행이 생기고, 포인트 사용 시 가장 오래된 행부터 `remaining`을 차감(FIFO)한다.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| user_id | varchar(36) FK→users.id | NO | | |
| order_id | varchar(36) FK→orders.id | YES | NULL | |
| points | int | NO | | 이 건에서 적립된 총량(불변) |
| remaining | int | NO | | 아직 사용/만료되지 않고 남은 양(FIFO 소진) |
| earned_at | datetime | NO | now() | 만료 기준 시각(이 값 + 30일 경과 시 만료 대상) |
| expired_at | datetime | YES | NULL | 만료 처리된 시각(안 됐으면 NULL) |
| created_at | datetime | NO | now() | |

---

## 2. 메뉴

### `categories`
| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| parent_id | varchar(36) FK→categories.id | YES | NULL | 계층 구조 지원용(현재 미사용, 전부 NULL) |
| name_ko / name_en | varchar(64) | NO | | |
| display_order | int | NO | 0 | |
| is_visible | tinyint(1) | NO | 1 | |
| image_url | varchar(255) | YES | NULL | |

현재 3개 시드(`backend/core/seed.py`): 버거(burger) / 사이드(side) / 음료(beverage).
`GET /api/menu` 응답의 `menu_items` 딕셔너리 키는 `name_en.lower()` — 즉 `burger`/`side`/`beverage`이며,
프론트(`menuService.js`)가 `beverage → drink`로 재매핑한다.

### `menu_items`
| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| category_id | varchar(36) FK→categories.id | NO | | |
| name_ko / name_en | varchar(128) | NO | | |
| base_price | decimal(12,2) | NO | | |
| description | text | NO | | 설명 문구 안에 칼로리가 텍스트로 포함(`"...칼로리 820kcal (세트 1170kcal)."`) — 별도 kcal 컬럼 없음 |
| image_url | varchar(255) | YES | NULL | 단품 이미지 경로(프론트 `public/images/...` 정적 파일을 가리키는 문자열, DB엔 경로만 저장) |
| set_image_url | varchar(255) | YES | NULL | 세트 구성 이미지 경로. NULL이면 프론트가 image_url로 대체 표시 |
| is_available | tinyint(1) | NO | 1 | 품절 처리(관리자가 끄면 주문 불가) |
| is_popular | tinyint(1) | NO | 0 | 추천메뉴 탭 + AI `list_popular_menu` 도구가 참조하는 필드 |
| is_new | tinyint(1) | NO | 0 | 현재 화면/AI 어디서도 실제로 활용 안 함(스키마만 존재) |
| display_order | int | NO | 0 | |
| created_at | datetime | NO | now() | |

현재 26개 시드(버거 13 + 사이드 6 + 음료 7). `is_popular=1`인 항목: F 버거, 게살 버거, 비건 버거.

### `menu_options`
메뉴 하나에 딸린 세트업그레이드/제외/세트사이드/세트음료 옵션을 전부 이 한 테이블에 저장.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| menu_item_id | varchar(36) FK→menu_items.id (ON DELETE CASCADE) | NO | | |
| name_ko / name_en | varchar(128) | NO | | |
| description | text | NO | | |
| additional_price | decimal(12,2) | NO | 0.00 | |
| is_available | tinyint(1) | NO | 1 | |
| display_order | int | NO | 0 | **정렬 기준으로 실제 사용됨** — `MenuItem.options` relationship에 `order_by`로 지정돼 있어, 이름이 서로의 부분 문자열인 옵션(예: "감자튀김"/"양념감자튀김")끼리 매칭이 꼬이지 않도록 보장 |
| option_group | enum(SET_UPGRADE,EXCLUDE,SET_SIDE,SET_DRINK) | NO | EXCLUDE | 옵션 종류 구분 |
| created_at | datetime | NO | now() | |

버거 13종(세트 가능) 기준 옵션 구성: SET_UPGRADE 1개(+2,000원) + SET_SIDE 4개(감자튀김/치즈스틱/
치킨너겟/양념감자튀김, 양념감자튀김만 +500원) + SET_DRINK 7개(콜라/제로콜라/사이다/제로사이다/
생수/뽀로로음료/오렌지주스, 오렌지주스만 +500원) + 재료별 EXCLUDE 옵션. 총 180행
(SET_UPGRADE 13 + SET_SIDE 52 + SET_DRINK 91 + EXCLUDE 24).

### `allergens`
식품위생법 표시 대상 알레르기 유발물질 19종 마스터 테이블(난류/우유/메밀/땅콩/대두/밀/고등어/
게/새우/돼지고기/복숭아/토마토/아황산류/호두/닭고기/쇠고기/오징어/조개류/잣 등).

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| code | varchar(32) UNIQUE | NO | | 예: EGG, MILK, WHEAT, SHRIMP |
| name_ko / name_en | varchar(32) | NO | | |
| display_order | int | NO | 0 | |

### `menu_item_allergens`
메뉴 ↔ 알레르기 유발물질 다대다 조인 테이블. `(menu_item_id, allergen_id)` 유니크.
AI의 `list_menu`/`search_menu` 도구 출력에 `[알레르기: 밀, 새우, ...]` 형태로 노출되어
"새우 알레르기인데 안전한 버거 추천해줘" 같은 질문에 실제 데이터 기반으로 답할 수 있게 한다.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| menu_item_id | varchar(36) FK→menu_items.id | NO | | |
| allergen_id | varchar(36) FK→allergens.id | NO | | |

---

## 3. 장바구니

### `carts`
비회원 주문 지원을 위해 `session_id`(프론트가 발급하는 세션 UUID)로 식별. 터치/음성 주문이
같은 `session_id`를 공유해 동일한 카트를 실시간으로 함께 본다.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| session_id | varchar(64), INDEX | NO | | |
| status | enum(ACTIVE,COMPLETED,ABANDONED) | NO | ACTIVE | |
| expires_at | datetime | YES | NULL | 현재 실제로 채우는 로직 없음 |
| created_at / updated_at | datetime | NO | now() | |
| active_session_key | varchar(64), **GENERATED STORED** | YES | (계산값) | `status='ACTIVE'`일 때만 `session_id` 값을 갖고 그 외엔 NULL. `UNIQUE KEY`로 걸려있어 **한 세션당 ACTIVE 카트가 동시에 2개 이상 생기는 경쟁 상태(음성으로 여러 add_item이 동시 호출되는 경우 등)를 DB 레벨에서 원천 차단**한다. COMPLETED/ABANDONED 카트는 NULL이라 여러 개 쌓여도 유니크 제약에 안 걸림 |

### `cart_items`
| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| cart_id | varchar(36) FK→carts.id (ON DELETE CASCADE) | NO | | |
| menu_item_id | varchar(36) FK→menu_items.id | NO | | |
| quantity | int | NO | 1 | |
| unit_price | decimal(12,2) | NO | | base_price + 선택된 옵션 additional_price 합산(서버가 계산, 클라이언트 신뢰 안 함) |
| selected_options | json | YES | NULL | `[{"option_id": "...", "name": "..."}]` 형태 배열 |
| special_note | text | YES | NULL | 음성 주문의 비정형 요구사항(예: "반으로 잘라주세요") 저장 |
| added_at | datetime | NO | now() | |

---

## 4. 주문 / 결제

### `orders`
| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| user_id | varchar(36) FK→users.id | YES | NULL | 비회원 주문이면 NULL |
| cart_id | varchar(36) FK→carts.id | YES | NULL | |
| order_number | varchar(32) UNIQUE | NO | | 당일 순번 문자열("1","2",...) |
| order_type | enum(EAT_IN,TAKE_OUT) | NO | TAKE_OUT | |
| table_number | int | YES | NULL | 매장 식사 테이블 번호 — 현재 입력 UI 없음(항상 NULL) |
| status | enum(RECEIVED,COOKING,READY,COMPLETED,CANCELLED) | NO | RECEIVED | 관리자 주문관리 API가 전이시킴(역행 금지 로직 존재) |
| user_coupon_id | varchar(36) FK→user_coupons.id | YES | NULL | 환불 시 포인트/쿠폰 원상복구를 위해 어떤 쿠폰을 썼는지 기록 |
| subtotal / discount_amount / final_amount | decimal(12,2) | NO | 0.00 | |
| points_used / points_earned | int | NO | 0 | earned는 final_amount의 5% |
| created_at | datetime | NO | now() | |

### `order_items`
`cart_items`와 거의 동일한 구조이되 주문 확정 시점의 스냅샷(카트가 이후 바뀌어도 영향 없음).

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| order_id | varchar(36) FK→orders.id (ON DELETE CASCADE) | NO | | |
| menu_item_id | varchar(36) FK→menu_items.id | NO | | |
| quantity / unit_price / total_price | | NO | | |
| selected_options | json | YES | NULL | |
| special_note | text | YES | NULL | |

### `payments`
PG 미연동 — `dao/payment_dao.py`가 요청받으면 무조건 `status=SUCCESS`로 즉시 처리(모의 결제).

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| order_id | varchar(36) FK→orders.id | NO | | |
| method | enum(CARD,SAMSUNG_PAY,QR_PAY,CASH) | NO | | 프론트 'pay'(간편결제)는 QR_PAY로 매핑 |
| amount | decimal(12,2) | NO | | |
| pg_transaction_id | varchar(128) UNIQUE | YES | NULL | |
| pg_provider | varchar(64) | YES | NULL | |
| status | enum(PENDING,SUCCESS,FAILED,REFUNDED) | NO | PENDING | |
| failure_reason | text | YES | NULL | |
| paid_at / refunded_at | datetime | YES | NULL | |
| created_at | datetime | NO | now() | |

---

## 5. 쿠폰 / 할인

### `coupons`
쿠폰 코드 마스터. 현재 데이터 0건(운영 중 관리자가 발급하는 용도, 시드 없음).

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| code | varchar(64) UNIQUE | NO | | `GET /api/orders/validate-coupon`, `POST /api/orders`가 조회 |
| discount_type | enum(CASH,PERCENT) | NO | | |
| discount_value | decimal(12,2) | NO | | |
| min_order_amount | decimal(12,2) | NO | 0.00 | |
| max_usage_count / used_count | int | NO | 0 | used_count 증가 로직은 현재 없음(스키마만 존재) |
| valid_from / valid_until | date | YES | NULL | 현재 API가 기간 검증은 안 함(활성 여부만 체크) |
| is_active | tinyint(1) | NO | 1 | |
| created_at | datetime | NO | now() | |

### `user_coupons`
특정 회원에게 발급된 쿠폰 보유 현황(다대다: 한 쿠폰 코드를 여러 회원에게 발급 가능).
현재 데이터 0건 — 발급 관리 API/UI가 아직 없음.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| user_id | varchar(36) FK→users.id | NO | | |
| coupon_id | varchar(36) FK→coupons.id | NO | | |
| is_used | tinyint(1) | NO | 0 | |
| used_at | datetime | YES | NULL | |
| issued_at | datetime | NO | now() | |

### `discounts`
메뉴/카테고리/전체 단위 상시 할인. 현재 데이터 0건, API에서도 아직 참조 안 함(스키마만 존재).

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| menu_item_id | varchar(36) FK→menu_items.id | YES | NULL | |
| category_id | varchar(36) FK→categories.id | YES | NULL | |
| target_type | enum(MENU,CATEGORY,ALL) | NO | | |
| discount_type | enum(CASH,PERCENT) | NO | | |
| discount_value | decimal(12,2) | NO | | |
| name_ko / name_en | varchar(128) | NO | | |
| valid_from / valid_until | date | YES | NULL | |
| applicable_tier | enum(ALL,STUDENT,SENIOR,GOLD) | NO | ALL | |
| is_active | tinyint(1) | NO | 1 | |
| created_at | datetime | NO | now() | |

---

## 6. 관리자

### `admin_users`
| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| username | varchar(64) UNIQUE | NO | | |
| password_hash | varchar(255) | NO | | bcrypt |
| display_name | varchar(64) | NO | | |
| role | enum(OWNER,STAFF) | NO | | `require_owner` 의존성은 정의만 되어있고 실제로 어느 라우터에도 안 걸려있어 권한 구분이 미완성 |
| is_active | tinyint(1) | NO | | |
| last_login_at | datetime | YES | NULL | |
| created_at | datetime | NO | now() | |

`backend/core/admin_seed.py`로 부트스트랩 계정 1개 시드됨.

---

## 7. 키오스크 설정

### `start_screen_images`
대기화면(StartScreen) 배경 슬라이드. `GET /api/settings/start-screen-images`가
`is_active=1`인 행을 `display_order` 순으로 반환하면 프론트가 5초 간격 크로스페이드로 순환
표시한다(1장뿐이면 순환 없이 고정 표시). **관리자 UI 없이 이 테이블에 행만 넣고 빼면 즉시 반영됨**
— 코드 배포 불필요.

| 컬럼 | 타입 | Null | 기본값 | 설명 |
|---|---|---|---|---|
| id | varchar(36) PK | NO | uuid | |
| image_url | varchar(255) | NO | | `/bg.png`처럼 프론트 `public/` 기준 정적 경로 문자열 |
| display_order | int | NO | 0 | |
| is_active | tinyint(1) | NO | 1 | |
| created_at | datetime | NO | now() | |

---

## 8. 현재 데이터 스냅샷 (행 수)

| 테이블 | 행 수 | 비고 |
|---|---:|---|
| users | 1 | 실제 사용자 주문에서 자동 생성된 회원 1명 |
| memberships | 0 | 미사용 |
| point_earn_logs | 1 | 위 회원의 실주문 적립 1건 |
| categories | 3 | 버거/사이드/음료 |
| menu_items | 26 | 버거13 + 사이드6 + 음료7 |
| menu_options | 180 | SET_UPGRADE 13 + SET_SIDE 52 + SET_DRINK 91 + EXCLUDE 24 |
| allergens | 19 | 식품위생법 표시 대상 전종 |
| menu_item_allergens | 56 | 메뉴-알레르기 매핑 |
| carts | 22 | 대부분 ACTIVE/ABANDONED 상태의 실사용 흔적 |
| cart_items | 16 | |
| orders | 2 | 실제 사용자 주문 2건(전화번호 동일 회원) |
| order_items | 2 | |
| payments | 2 | |
| coupons | 0 | 아직 발급된 쿠폰 없음 |
| user_coupons | 0 | |
| discounts | 0 | |
| admin_users | 1 | 부트스트랩 계정 |
| start_screen_images | 1 | `/bg.png` |

> 이 표는 문서 작성 시점 스냅샷이며 실사용에 따라 계속 변한다. 최신 값이 필요하면
> `SELECT COUNT(*) FROM <table>;`로 직접 조회할 것.
