"""
DB 스키마 (스키마 명세서 13 테이블).

- 비회원 주문을 지원하기 위해 CARTS 는 session_id 로 식별.
- CART_ITEMS.special_note / ORDER_ITEMS.special_note 는 음성 비정형 요구사항 저장.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Computed,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# --- USERS ---------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accessibility_mode: Mapped[str] = mapped_column(
        SAEnum("NORMAL", "VOICE_GUIDE", "HIGH_CONTRAST", "LARGE_TEXT", name="accessibility_mode"),
        default="NORMAL",
    )
    preferred_language: Mapped[str] = mapped_column(
        SAEnum("ko", "en", "zh", "ja", name="preferred_language"), default="ko"
    )
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True)
    current_points: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# --- MEMBERSHIPS ---------------------------------------------------------
class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    tier: Mapped[str] = mapped_column(
        SAEnum("BASIC", "SILVER", "GOLD", name="membership_tier"), default="BASIC"
    )
    points: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# --- POINT_EARN_LOGS ------------------------------------------------------
class PointEarnLog(Base):
    """포인트 적립 내역 원장 — 적립분마다 한 건씩 남겨 30일 경과 시 만료 처리한다.

    remaining 은 이 적립분 중 아직 사용/만료되지 않고 남은 포인트(FIFO로 소진).
    """
    __tablename__ = "point_earn_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orders.id"), nullable=True)
    points: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    earned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# --- COUPONS -------------------------------------------------------------
class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    discount_type: Mapped[str] = mapped_column(
        SAEnum("CASH", "PERCENT", name="coupon_discount_type")
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    min_order_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    max_usage_count: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# --- USER_COUPONS --------------------------------------------------------
class UserCoupon(Base):
    __tablename__ = "user_coupons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    coupon_id: Mapped[str] = mapped_column(String(36), ForeignKey("coupons.id"))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    coupon: Mapped["Coupon"] = relationship("Coupon")


# --- CATEGORIES ----------------------------------------------------------
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=True
    )
    name_ko: Mapped[str] = mapped_column(String(64))
    name_en: Mapped[str] = mapped_column(String(64))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)


# --- MENU_ITEMS ----------------------------------------------------------
class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id"))
    name_ko: Mapped[str] = mapped_column(String(128))
    name_en: Mapped[str] = mapped_column(String(128))
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 세트로 담을 때 보여줄 이미지(버거+사이드+음료 구성 사진). 없으면 image_url로 대체.
    set_image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # display_order로 정렬 — UUID PK라 정렬을 지정하지 않으면 반환 순서가 삽입 순서와
    # 무관해져서(InnoDB는 PK 순으로 반환), "감자튀김"/"양념감자튀김"처럼 이름이 서로의 부분
    # 문자열인 옵션끼리 순서가 뒤섞여 음성 주문의 이름 매칭이 비결정적으로 틀리는 문제가 있었다.
    options: Mapped[list["MenuOption"]] = relationship(
        "MenuOption", back_populates="menu_item", cascade="all,delete-orphan",
        order_by="MenuOption.display_order",
    )
    category: Mapped["Category"] = relationship("Category")
    allergen_links: Mapped[list["MenuItemAllergen"]] = relationship(
        "MenuItemAllergen", back_populates="menu_item", cascade="all,delete-orphan"
    )

    @property
    def allergens(self) -> list["Allergen"]:
        """MenuItemOut(from_attributes) 이 조인 테이블을 몰라도 바로 쓸 수 있도록 평탄화.
        allergen_links가 selectinload로 미리 로드되어 있어야 한다(지연 로딩 시 비동기 오류)."""
        return [link.allergen for link in self.allergen_links]


# --- MENU_OPTIONS --------------------------------------------------------
class MenuOption(Base):
    __tablename__ = "menu_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    menu_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("menu_items.id"))
    name_ko: Mapped[str] = mapped_column(String(128))
    name_en: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    additional_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    # 세트 구성 시 옵션이 세트 업그레이드/재료 제외/사이드 선택/음료 선택 중 무엇인지 구분
    option_group: Mapped[str] = mapped_column(
        SAEnum("SET_UPGRADE", "EXCLUDE", "SET_SIDE", "SET_DRINK", name="menu_option_group"),
        default="EXCLUDE",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="options")


# --- ALLERGENS -------------------------------------------------------------
class Allergen(Base):
    """식품위생법 표시 대상 알레르기 유발물질 19종 마스터 테이블."""
    __tablename__ = "allergens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # 예: EGG, MILK, WHEAT
    name_ko: Mapped[str] = mapped_column(String(32))
    name_en: Mapped[str] = mapped_column(String(32))
    display_order: Mapped[int] = mapped_column(Integer, default=0)


# --- MENU_ITEM_ALLERGENS -----------------------------------------------------
class MenuItemAllergen(Base):
    """메뉴-알레르기 유발물질 매핑(다대다 조인 테이블)."""
    __tablename__ = "menu_item_allergens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    menu_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("menu_items.id"))
    allergen_id: Mapped[str] = mapped_column(String(36), ForeignKey("allergens.id"))

    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="allergen_links")
    allergen: Mapped["Allergen"] = relationship("Allergen")

    __table_args__ = (
        UniqueConstraint("menu_item_id", "allergen_id", name="uq_menu_item_allergen"),
    )


# --- DISCOUNTS -----------------------------------------------------------
class Discount(Base):
    __tablename__ = "discounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    menu_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("menu_items.id"), nullable=True
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=True
    )
    target_type: Mapped[str] = mapped_column(
        SAEnum("MENU", "CATEGORY", "ALL", name="discount_target_type")
    )
    discount_type: Mapped[str] = mapped_column(
        SAEnum("CASH", "PERCENT", name="discount_value_type")
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    name_ko: Mapped[str] = mapped_column(String(128))
    name_en: Mapped[str] = mapped_column(String(128))
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    applicable_tier: Mapped[str] = mapped_column(
        SAEnum("ALL", "STUDENT", "SENIOR", "GOLD", name="discount_applicable_tier"),
        default="ALL",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# --- CARTS ---------------------------------------------------------------
class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(
        SAEnum("ACTIVE", "COMPLETED", "ABANDONED", name="cart_status"), default="ACTIVE"
    )
    # session_id 당 ACTIVE 카트가 동시에 여러 개 생기는 것을 DB 차원에서 막기 위한 생성 컬럼.
    # ACTIVE 상태일 때만 session_id 값을 갖고 그 외엔 NULL(MySQL 유니크 인덱스는 NULL을 여러 개
    # 허용하므로 완료/폐기된 카트가 여러 개 쌓이는 건 문제없음) — 한 발화에서 여러 개의
    # add_item 툴이 동시 호출돼 같은 세션에 ACTIVE 카트가 중복 생성되던 버그(경쟁 상태) 수정.
    active_session_key: Mapped[str | None] = mapped_column(
        String(64),
        Computed("CASE WHEN status = 'ACTIVE' THEN session_id ELSE NULL END", persisted=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("active_session_key", name="uq_carts_active_session"),
    )

    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="cart", cascade="all,delete-orphan"
    )


# --- CART_ITEMS ----------------------------------------------------------
class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cart_id: Mapped[str] = mapped_column(String(36), ForeignKey("carts.id"))
    menu_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("menu_items.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    selected_options: Mapped[list | None] = mapped_column(JSON, default=list)
    # ★배리어프리: 음성에서 추출된 비정형 요구사항
    special_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem")


# --- ORDERS --------------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    cart_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("carts.id"), nullable=True
    )
    order_number: Mapped[str] = mapped_column(String(32), unique=True)
    order_type: Mapped[str] = mapped_column(
        SAEnum("EAT_IN", "TAKE_OUT", name="order_type"), default="TAKE_OUT"
    )
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("RECEIVED", "COOKING", "READY", "COMPLETED", "CANCELLED", name="order_status"),
        default="RECEIVED",
    )
    # 환불 시 포인트·쿠폰을 정확히 원상복구하려면 이 주문에 어떤 쿠폰을 썼는지가 남아있어야 한다.
    user_coupon_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("user_coupons.id"), nullable=True
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    final_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    points_used: Mapped[int] = mapped_column(Integer, default=0)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all,delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="order")


# --- ORDER_ITEMS ---------------------------------------------------------
class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"))
    menu_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("menu_items.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    selected_options: Mapped[list | None] = mapped_column(JSON, default=list)
    special_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem")


# --- PAYMENTS ------------------------------------------------------------
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"))
    method: Mapped[str] = mapped_column(
        SAEnum("CARD", "SAMSUNG_PAY", "QR_PAY", "CASH", name="payment_method")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    pg_transaction_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    pg_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("PENDING", "SUCCESS", "FAILED", "REFUNDED", name="payment_status"),
        default="PENDING",
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped["Order"] = relationship("Order", back_populates="payments")


# --- ADMIN_USERS -----------------------------------------------------------
class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(
        SAEnum("OWNER", "STAFF", name="admin_role"), default="STAFF"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# --- START_SCREEN_IMAGES ---------------------------------------------------
class StartScreenImage(Base):
    """대기화면(StartScreen) 배경 슬라이드 — 여러 장이면 프론트가 순서대로 크로스페이드 순환한다.

    관리자가 나중에 이미지를 교체/추가/비활성화할 수 있도록 DB로 관리한다(코드 수정 불필요).
    """
    __tablename__ = "start_screen_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    image_url: Mapped[str] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
