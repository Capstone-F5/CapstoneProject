-- ============================================================
-- F5 키오스크 MySQL 초기화 스크립트
-- 실행 순서: 이 파일 하나만 실행하면 DB + 테이블 + 시드 데이터 완성
-- 실행 방법: mysql -u root -p < database/init.sql
-- ============================================================

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS kiosk_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE kiosk_db;

-- ============================================================
-- 테이블 생성 (FK 의존 순서 준수)
-- ============================================================

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id                 VARCHAR(36)  NOT NULL PRIMARY KEY,
    phone_number       VARCHAR(32)  NULL UNIQUE,
    accessibility_mode ENUM('NORMAL','VOICE_GUIDE','HIGH_CONTRAST','LARGE_TEXT')
                                    NOT NULL DEFAULT 'NORMAL',
    preferred_language ENUM('ko','en','zh','ja')
                                    NOT NULL DEFAULT 'ko',
    is_guest           TINYINT(1)   NOT NULL DEFAULT 1,
    current_points     INT          NOT NULL DEFAULT 0,
    created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. MEMBERSHIPS
CREATE TABLE IF NOT EXISTS memberships (
    id         VARCHAR(36) NOT NULL PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL,
    tier       ENUM('BASIC','SILVER','GOLD') NOT NULL DEFAULT 'BASIC',
    points     INT         NOT NULL DEFAULT 0,
    updated_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_memberships_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. COUPONS
CREATE TABLE IF NOT EXISTS coupons (
    id               VARCHAR(36)    NOT NULL PRIMARY KEY,
    code             VARCHAR(64)    NOT NULL UNIQUE,
    discount_type    ENUM('CASH','PERCENT') NOT NULL,
    discount_value   DECIMAL(12, 2) NOT NULL,
    min_order_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    max_usage_count  INT            NOT NULL DEFAULT 0,
    used_count       INT            NOT NULL DEFAULT 0,
    valid_from       DATE           NULL,
    valid_until      DATE           NULL,
    is_active        TINYINT(1)     NOT NULL DEFAULT 1,
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. USER_COUPONS
CREATE TABLE IF NOT EXISTS user_coupons (
    id         VARCHAR(36) NOT NULL PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL,
    coupon_id  VARCHAR(36) NOT NULL,
    is_used    TINYINT(1)  NOT NULL DEFAULT 0,
    used_at    DATETIME    NULL,
    issued_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_uc_user   FOREIGN KEY (user_id)   REFERENCES users   (id),
    CONSTRAINT fk_uc_coupon FOREIGN KEY (coupon_id) REFERENCES coupons (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. CATEGORIES (self-referencing)
CREATE TABLE IF NOT EXISTS categories (
    id            VARCHAR(36)  NOT NULL PRIMARY KEY,
    parent_id     VARCHAR(36)  NULL,
    name_ko       VARCHAR(64)  NOT NULL,
    name_en       VARCHAR(64)  NOT NULL,
    display_order INT          NOT NULL DEFAULT 0,
    is_visible    TINYINT(1)   NOT NULL DEFAULT 1,
    image_url     VARCHAR(255) NULL,
    CONSTRAINT fk_categories_parent FOREIGN KEY (parent_id) REFERENCES categories (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. MENU_ITEMS
CREATE TABLE IF NOT EXISTS menu_items (
    id            VARCHAR(36)    NOT NULL PRIMARY KEY,
    category_id   VARCHAR(36)    NOT NULL,
    name_ko       VARCHAR(128)   NOT NULL,
    name_en       VARCHAR(128)   NOT NULL,
    base_price    DECIMAL(12, 2) NOT NULL,
    description   TEXT           NOT NULL DEFAULT '',
    image_url     VARCHAR(255)   NULL,
    is_available  TINYINT(1)     NOT NULL DEFAULT 1,
    is_popular    TINYINT(1)     NOT NULL DEFAULT 0,
    is_new        TINYINT(1)     NOT NULL DEFAULT 0,
    display_order INT            NOT NULL DEFAULT 0,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_menu_items_category FOREIGN KEY (category_id) REFERENCES categories (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. MENU_OPTIONS
CREATE TABLE IF NOT EXISTS menu_options (
    id               VARCHAR(36)    NOT NULL PRIMARY KEY,
    menu_item_id     VARCHAR(36)    NOT NULL,
    name_ko          VARCHAR(128)   NOT NULL,
    name_en          VARCHAR(128)   NOT NULL,
    description      TEXT           NOT NULL DEFAULT '',
    additional_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
    is_available     TINYINT(1)     NOT NULL DEFAULT 1,
    display_order    INT            NOT NULL DEFAULT 0,
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_menu_options_item FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. DISCOUNTS
CREATE TABLE IF NOT EXISTS discounts (
    id               VARCHAR(36)    NOT NULL PRIMARY KEY,
    menu_item_id     VARCHAR(36)    NULL,
    category_id      VARCHAR(36)    NULL,
    target_type      ENUM('MENU','CATEGORY','ALL') NOT NULL,
    discount_type    ENUM('CASH','PERCENT')        NOT NULL,
    discount_value   DECIMAL(12, 2) NOT NULL,
    name_ko          VARCHAR(128)   NOT NULL,
    name_en          VARCHAR(128)   NOT NULL,
    valid_from       DATE           NULL,
    valid_until      DATE           NULL,
    applicable_tier  ENUM('ALL','STUDENT','SENIOR','GOLD') NOT NULL DEFAULT 'ALL',
    is_active        TINYINT(1)     NOT NULL DEFAULT 1,
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_discounts_item     FOREIGN KEY (menu_item_id) REFERENCES menu_items  (id),
    CONSTRAINT fk_discounts_category FOREIGN KEY (category_id)  REFERENCES categories  (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. CARTS
CREATE TABLE IF NOT EXISTS carts (
    id         VARCHAR(36) NOT NULL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    status     ENUM('ACTIVE','COMPLETED','ABANDONED') NOT NULL DEFAULT 'ACTIVE',
    expires_at DATETIME    NULL,
    created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_carts_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. CART_ITEMS
CREATE TABLE IF NOT EXISTS cart_items (
    id               VARCHAR(36)    NOT NULL PRIMARY KEY,
    cart_id          VARCHAR(36)    NOT NULL,
    menu_item_id     VARCHAR(36)    NOT NULL,
    quantity         INT            NOT NULL DEFAULT 1,
    unit_price       DECIMAL(12, 2) NOT NULL,
    selected_options JSON           NULL,
    special_note     TEXT           NULL,
    added_at         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id)      REFERENCES carts      (id) ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_menu FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. ORDERS
CREATE TABLE IF NOT EXISTS orders (
    id              VARCHAR(36)    NOT NULL PRIMARY KEY,
    user_id         VARCHAR(36)    NULL,
    cart_id         VARCHAR(36)    NULL,
    order_number    VARCHAR(32)    NOT NULL UNIQUE,
    order_type      ENUM('EAT_IN','TAKE_OUT') NOT NULL DEFAULT 'TAKE_OUT',
    table_number    INT            NULL,
    subtotal        DECIMAL(12, 2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    final_amount    DECIMAL(12, 2) NOT NULL DEFAULT 0,
    points_used     INT            NOT NULL DEFAULT 0,
    points_earned   INT            NOT NULL DEFAULT 0,
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_orders_cart FOREIGN KEY (cart_id) REFERENCES carts (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. ORDER_ITEMS
CREATE TABLE IF NOT EXISTS order_items (
    id               VARCHAR(36)    NOT NULL PRIMARY KEY,
    order_id         VARCHAR(36)    NOT NULL,
    menu_item_id     VARCHAR(36)    NOT NULL,
    quantity         INT            NOT NULL,
    unit_price       DECIMAL(12, 2) NOT NULL,
    total_price      DECIMAL(12, 2) NOT NULL,
    selected_options JSON           NULL,
    special_note     TEXT           NULL,
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id)     REFERENCES orders     (id) ON DELETE CASCADE,
    CONSTRAINT fk_order_items_menu  FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. PAYMENTS
CREATE TABLE IF NOT EXISTS payments (
    id                 VARCHAR(36)    NOT NULL PRIMARY KEY,
    order_id           VARCHAR(36)    NOT NULL,
    method             ENUM('CARD','SAMSUNG_PAY','QR_PAY','CASH') NOT NULL,
    amount             DECIMAL(12, 2) NOT NULL,
    pg_transaction_id  VARCHAR(128)   NULL UNIQUE,
    pg_provider        VARCHAR(64)    NULL,
    status             ENUM('PENDING','SUCCESS','FAILED','REFUNDED') NOT NULL DEFAULT 'PENDING',
    failure_reason     TEXT           NULL,
    paid_at            DATETIME       NULL,
    refunded_at        DATETIME       NULL,
    created_at         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 시드 데이터 (카테고리 → 메뉴 → 옵션 순서)
-- UUIDv4는 Python seed.py로 자동 생성되므로
-- 여기서는 고정 UUID를 사용해 참조 관계를 명확히 함
-- ============================================================

-- 카테고리
INSERT IGNORE INTO categories (id, name_ko, name_en, display_order, is_visible) VALUES
    ('cat-burger-0001-0000-000000000001', '버거',   'Burger',   1, 1),
    ('cat-side--0001-0000-000000000002', '사이드', 'Side',     2, 1),
    ('cat-bev---0001-0000-000000000003', '음료',   'Beverage', 3, 1);

-- 메뉴 아이템 (버거)
INSERT IGNORE INTO menu_items
    (id, category_id, name_ko, name_en, base_price, description, is_available, is_popular, display_order)
VALUES
    ('item-fbur--0001-0000-000000000001', 'cat-burger-0001-0000-000000000001',
     'F 버거', 'F Burger', 7500,
     '[F 버거] 치킨과 불고기의 만남, 한 입에 끝내는 환상의 더블 콤보! 주요 재료: 치킨패티, 불고기패티, 불고기소스. 칼로리 820kcal (세트 1170kcal).',
     1, 1, 1),

    ('item-grbf--0001-0000-000000000002', 'cat-burger-0001-0000-000000000001',
     '그릴드 비프 버거', 'Grilled Beef Burger', 7800,
     '[그릴드 비프 버거] 진짜 불맛을 원한다면? 그릴 자국 선명한 정통 수제 패티! 주요 재료: 그릴드 비프 패티, 체다치즈, 적양파. 칼로리 710kcal (세트 1060kcal).',
     1, 0, 2),

    ('item-mozz--0001-0000-000000000003', 'cat-burger-0001-0000-000000000001',
     '모짜렐라 버거', 'Mozzarella Burger', 7200,
     '[모짜렐라 버거] 치즈 폭포가 팡팡! 고소한 통치즈가 쭈욱 늘어나는 즐거움. 주요 재료: 소고기패티, 통모짜렐라 튀김, 마리나라. 칼로리 780kcal (세트 1130kcal).',
     1, 0, 3),

    ('item-vega--0001-0000-000000000004', 'cat-burger-0001-0000-000000000001',
     '비건 버거', 'Vegan Burger', 6800,
     '[비건 버거] 지구와 나를 위한 선택, 고기 없이도 완벽한 풍미와 건강함. 주요 재료: 식물성패티, 통밀번, 아보카도. 칼로리 420kcal (세트 770kcal).',
     1, 0, 4),

    ('item-crab--0001-0000-000000000005', 'cat-burger-0001-0000-000000000001',
     '게살 버거', 'Crab Burger', 6500,
     '[게살 버거] 입안 가득 번지는 바다의 향기, 겉바속촉 게살의 진수! 주요 재료: 게살 튀김 패티, 타르타르 소스. 칼로리 550kcal (세트 900kcal).',
     1, 0, 5),

    ('item-ckth--0001-0000-000000000006', 'cat-burger-0001-0000-000000000001',
     '치킨 다릿살 버거', 'Chicken Thigh Burger', 6200,
     '[치킨 다릿살 버거] 퍽퍽함 제로! 야들야들한 닭다리살의 육즙이 살아있는 버거. 주요 재료: 닭다리살 튀김, 마요네즈. 칼로리 650kcal (세트 1000kcal).',
     1, 0, 6),

    ('item-dblg--0001-0000-000000000007', 'cat-burger-0001-0000-000000000001',
     '더블 불고기 버거', 'Double Bulgogi Burger', 6000,
     '[더블 불고기 버거] 더 진해진 달콤짭짤함, 불고기 매니아를 위한 두 배의 감동. 주요 재료: 불고기 패티 2장, 불고기 소스. 칼로리 680kcal (세트 1030kcal).',
     1, 0, 7),

    ('item-dbch--0001-0000-000000000008', 'cat-burger-0001-0000-000000000001',
     '더블 치즈 버거', 'Double Cheese Burger', 5500,
     '[더블 치즈 버거] 치즈의 진한 풍미와 고소한 패티가 두 장씩! 치즈 덕후 필수. 주요 재료: 소고기 패티 2장, 치즈 2장, 피클. 칼로리 620kcal (세트 970kcal).',
     1, 0, 8),

    ('item-ckbs--0001-0000-000000000009', 'cat-burger-0001-0000-000000000001',
     '치킨 가슴살 버거', 'Chicken Breast Burger', 5500,
     '[치킨 가슴살 버거] 담백함의 끝판왕! 크런치한 식감 뒤에 숨겨진 부드러운 속살. 주요 재료: 닭가슴살 튀김, 크리미 화이트 소스. 칼로리 520kcal (세트 870kcal).',
     1, 0, 9),

    ('item-shmp--0001-0000-000000000010', 'cat-burger-0001-0000-000000000001',
     '새우 버거', 'Shrimp Burger', 4800,
     '[새우 버거] 탱글탱글 씹히는 통새우살, 고소함이 남다른 마성의 버거. 주요 재료: 새우 패티, 타르타르 소스. 칼로리 480kcal (세트 830kcal).',
     1, 1, 10),

    ('item-blgo--0001-0000-000000000011', 'cat-burger-0001-0000-000000000001',
     '불고기 버거', 'Bulgogi Burger', 4500,
     '[불고기 버거] 한국인의 소울 푸드! 변치 않는 달콤함의 베스트셀러. 주요 재료: 불고기 패티 1장, 불고기 소스. 칼로리 450kcal (세트 800kcal).',
     1, 1, 11),

    ('item-chez--0001-0000-000000000012', 'cat-burger-0001-0000-000000000001',
     '치즈 버거', 'Cheese Burger', 4200,
     '[치즈 버거] 심플한게 제일 맛있지! 정통 아메리칸 스타일의 치즈버거. 주요 재료: 소고기 패티, 체다치즈, 케첩, 머스타드. 칼로리 430kcal (세트 780kcal).',
     1, 1, 12),

    ('item-teri--0001-0000-000000000013', 'cat-burger-0001-0000-000000000001',
     '데리버거', 'Teri Burger', 4000,
     '[데리버거] 달콤짭짤한 데리야끼 소스와 부드러운 패티의 환상적인 조화! 주요 재료: 혼합육 패티, 데리야끼 소스, 마요네즈. 칼로리 410kcal (세트 760kcal).',
     1, 0, 13);

-- 메뉴 아이템 (사이드)
INSERT IGNORE INTO menu_items
    (id, category_id, name_ko, name_en, base_price, description, is_available, display_order)
VALUES
    ('item-sfri--0001-0000-000000000014', 'cat-side--0001-0000-000000000002',
     '양념감자튀김', 'Seasoned French Fries', 2500,
     '[양념감자튀김] 흔들어 먹는 재미! 입안에 착 붙는 마법의 가루 시즈닝. 380kcal.',
     1, 1),

    ('item-nugg--0001-0000-000000000015', 'cat-side--0001-0000-000000000002',
     '너겟(4조각)', 'Chicken Nuggets (4pcs)', 2000,
     '[너겟 4조각] 한 입에 쏙! 아이들도 좋아하는 바삭하고 담백한 간식. 180kcal.',
     1, 2),

    ('item-csti--0001-0000-000000000016', 'cat-side--0001-0000-000000000002',
     '치즈스틱(2개)', 'Cheese Sticks (2pcs)', 2000,
     '[치즈스틱 2개] 황금빛으로 잘 튀겨진 고소한 치즈가 쭈욱 늘어나는 맛. 160kcal.',
     1, 3),

    ('item-frim--0001-0000-000000000017', 'cat-side--0001-0000-000000000002',
     '감자튀김(M)', 'French Fries (M)', 2000,
     '[감자튀김 M] 갓 튀겨내어 바삭함이 살아있는 햄버거의 영원한 단짝. 350kcal.',
     1, 4),

    ('item-corn--0001-0000-000000000018', 'cat-side--0001-0000-000000000002',
     '콘샐러드', 'Corn Salad', 1900,
     '[콘샐러드] 톡톡 터지는 옥수수 알갱이의 상큼함이 입안을 리프레쉬! 140kcal.',
     1, 5),

    ('item-cole--0001-0000-000000000019', 'cat-side--0001-0000-000000000002',
     '코울슬로', 'Cole Slaw', 1900,
     '[코울슬로] 아삭아삭 씹는 맛이 일품! 버거와 최고의 궁합 샐러드. 130kcal.',
     1, 6);

-- 메뉴 아이템 (음료)
INSERT IGNORE INTO menu_items
    (id, category_id, name_ko, name_en, base_price, description, is_available, display_order)
VALUES
    ('item-ojui--0001-0000-000000000020', 'cat-bev---0001-0000-000000000003',
     '오렌지 주스', 'Orange Juice', 2500,
     '[오렌지 주스] 상큼달콤 비타민 충전! 100% 신선한 과즙. 110kcal.',
     1, 1),

    ('item-cola--0001-0000-000000000021', 'cat-bev---0001-0000-000000000003',
     '콜라(M)', 'Coca Cola (M)', 2000,
     '[콜라 M] 얼음 가득 채운 짜릿한 탄산, 버거 맛을 200% 살려줘요. 140kcal.',
     1, 2),

    ('item-zcol--0001-0000-000000000022', 'cat-bev---0001-0000-000000000003',
     '제로 콜라(M)', 'Zero Coke (M)', 2000,
     '[제로 콜라 M] 맛은 그대로, 칼로리는 0! 부담 없이 즐기는 청량함.',
     1, 3),

    ('item-spri--0001-0000-000000000023', 'cat-bev---0001-0000-000000000003',
     '사이다(M)', 'Sprite (M)', 2000,
     '[사이다 M] 투명하고 맑은 깨끗한 탄산의 정석, 입안이 깔끔해져요. 130kcal.',
     1, 4),

    ('item-zspr--0001-0000-000000000024', 'cat-bev---0001-0000-000000000003',
     '제로 사이다(M)', 'Zero Sprite (M)', 2000,
     '[제로 사이다 M] 칼로리 걱정 끝! 가볍고 시원하게 터지는 청량 에너지.',
     1, 5),

    ('item-poro--0001-0000-000000000025', 'cat-bev---0001-0000-000000000003',
     '뽀로로 음료수', 'Pororo Drink', 2000,
     '[뽀로로 음료수] 어린이 친구들의 최애 메뉴! 귀여운 캐릭터와 달콤한 맛. 120kcal.',
     1, 6),

    ('item-watr--0001-0000-000000000026', 'cat-bev---0001-0000-000000000003',
     '생수', 'Mineral Water', 1000,
     '[생수] 갈증을 시원하게 풀어주는 맑고 투명한 순수한 물.',
     1, 7);

-- ============================================================
-- 메뉴 옵션 (세트 업그레이드 + 채소 제외)
-- ============================================================

INSERT IGNORE INTO menu_options
    (id, menu_item_id, name_ko, name_en, description, additional_price, display_order)
VALUES
-- F 버거
    ('opt-fbur-set-000000000000000001', 'item-fbur--0001-0000-000000000001', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-fbur-let-000000000000000002', 'item-fbur--0001-0000-000000000001', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-fbur-oni-000000000000000003', 'item-fbur--0001-0000-000000000001', '양파 제외', 'Exclude Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),

-- 그릴드 비프 버거
    ('opt-grbf-set-000000000000000004', 'item-grbf--0001-0000-000000000002', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-grbf-let-000000000000000005', 'item-grbf--0001-0000-000000000002', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-grbf-tom-000000000000000006', 'item-grbf--0001-0000-000000000002', '토마토 제외', 'Exclude Tomato', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),
    ('opt-grbf-ron-000000000000000007', 'item-grbf--0001-0000-000000000002', '적양파 제외', 'Exclude Red Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 3),

-- 모짜렐라 버거
    ('opt-mozz-set-000000000000000008', 'item-mozz--0001-0000-000000000003', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-mozz-let-000000000000000009', 'item-mozz--0001-0000-000000000003', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),

-- 비건 버거
    ('opt-vega-set-000000000000000010', 'item-vega--0001-0000-000000000004', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-vega-let-000000000000000011', 'item-vega--0001-0000-000000000004', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-vega-tom-000000000000000012', 'item-vega--0001-0000-000000000004', '토마토 제외', 'Exclude Tomato', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),
    ('opt-vega-ron-000000000000000013', 'item-vega--0001-0000-000000000004', '적양파 제외', 'Exclude Red Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 3),

-- 게살 버거
    ('opt-crab-set-000000000000000014', 'item-crab--0001-0000-000000000005', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-crab-let-000000000000000015', 'item-crab--0001-0000-000000000005', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),

-- 치킨 다릿살 버거
    ('opt-ckth-set-000000000000000016', 'item-ckth--0001-0000-000000000006', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-ckth-cab-000000000000000017', 'item-ckth--0001-0000-000000000006', '양배추 제외', 'Exclude Cabbage', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),

-- 더블 불고기 버거
    ('opt-dblg-set-000000000000000018', 'item-dblg--0001-0000-000000000007', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-dblg-let-000000000000000019', 'item-dblg--0001-0000-000000000007', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-dblg-oni-000000000000000020', 'item-dblg--0001-0000-000000000007', '양파 제외', 'Exclude Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),

-- 더블 치즈 버거
    ('opt-dbch-set-000000000000000021', 'item-dbch--0001-0000-000000000008', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-dbch-don-000000000000000022', 'item-dbch--0001-0000-000000000008', '다진 양파 제외', 'Exclude Diced Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-dbch-pik-000000000000000023', 'item-dbch--0001-0000-000000000008', '피클 제외', 'Exclude Pickles', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),

-- 치킨 가슴살 버거
    ('opt-ckbs-set-000000000000000024', 'item-ckbs--0001-0000-000000000009', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-ckbs-let-000000000000000025', 'item-ckbs--0001-0000-000000000009', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-ckbs-pik-000000000000000026', 'item-ckbs--0001-0000-000000000009', '피클 제외', 'Exclude Pickles', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),

-- 새우 버거
    ('opt-shmp-set-000000000000000027', 'item-shmp--0001-0000-000000000010', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-shmp-cab-000000000000000028', 'item-shmp--0001-0000-000000000010', '채썬 양배추 제외', 'Exclude Cabbage', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),

-- 불고기 버거
    ('opt-blgo-set-000000000000000029', 'item-blgo--0001-0000-000000000011', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-blgo-let-000000000000000030', 'item-blgo--0001-0000-000000000011', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-blgo-oni-000000000000000031', 'item-blgo--0001-0000-000000000011', '양파 제외', 'Exclude Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),

-- 치즈 버거
    ('opt-chez-set-000000000000000032', 'item-chez--0001-0000-000000000012', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-chez-don-000000000000000033', 'item-chez--0001-0000-000000000012', '다진 양파 제외', 'Exclude Diced Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-chez-pik-000000000000000034', 'item-chez--0001-0000-000000000012', '피클 제외', 'Exclude Pickles', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2),

-- 데리버거
    ('opt-teri-set-000000000000000035', 'item-teri--0001-0000-000000000013', '세트 업그레이드', 'Upgrade to Set', '세트 음료 및 사이드(감자튀김 M) 포함', 2000, 0),
    ('opt-teri-let-000000000000000036', 'item-teri--0001-0000-000000000013', '양상추 제외', 'Exclude Lettuce', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 1),
    ('opt-teri-oni-000000000000000037', 'item-teri--0001-0000-000000000013', '양파 제외', 'Exclude Onion', '알레르기 및 고령자 섭취 불편 호소 시 대화형 자동 차단 옵션', 0, 2);

-- ============================================================
-- 완료 확인 쿼리
-- ============================================================
SELECT '=== 초기화 완료 ===' AS status;
SELECT CONCAT(COUNT(*), '개 카테고리') AS result FROM categories
UNION ALL
SELECT CONCAT(COUNT(*), '개 메뉴') FROM menu_items
UNION ALL
SELECT CONCAT(COUNT(*), '개 옵션') FROM menu_options;
