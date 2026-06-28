# DB 파트 작업 명세

> **담당자:** 서유민 (+ 추가 인원)  
> **브랜치:** `feature/db-api-server`  
> **목표:** 프론트엔드와 LLM Agent가 실제 DB를 조회·조작할 수 있는 REST API 제공  
> **착수 전 읽기:** `docs/PM_사전작업.md` — API 응답 스펙이 거기 확정되어 있음

---

## 이미 완성된 것 (건드리지 말 것)

| 파일 | 내용 |
|---|---|
| `backend/core/models.py` | ORM 모델 13개 테이블 완성. 수정 불필요 |
| `backend/core/seed.py` | 메뉴·옵션 시드 데이터 완성. 수정 불필요 |
| `backend/core/db.py` | `get_db()` 의존성 주입, `init_db()` lifespan 호출 완성 |

---

## 새로 만들 파일 목록

```
backend/
  schemas/
    menu_schemas.py       ← 1순위
    cart_schemas.py       ← 2순위
    order_schemas.py      ← 3순위
    payment_schemas.py    ← 4순위
    user_schemas.py       ← 5순위
  dao/
    menu_dao.py           ← 1순위
    cart_dao.py           ← 2순위
    order_dao.py          ← 3순위
    payment_dao.py        ← 4순위
    user_dao.py           ← 5순위
  api/
    menu.py               ← 1순위
    cart.py               ← 2순위
    order.py              ← 3순위
    payment.py            ← 4순위
    user.py               ← 5순위
```

---

## 구현 명세

### 1단계: schemas/ (Pydantic DTO)

**원칙:** 모든 API 응답은 반드시 Pydantic 모델로 직렬화한다. ORM 모델을 직접 반환하지 않는다.

#### `backend/schemas/menu_schemas.py`

```python
from pydantic import BaseModel
from decimal import Decimal

class MenuOptionOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    additional_price: Decimal
    is_available: bool
    display_order: int

    model_config = {"from_attributes": True}

class MenuItemOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    base_price: Decimal
    description: str
    image_url: str | None
    is_available: bool
    is_popular: bool
    is_new: bool
    display_order: int
    options: list[MenuOptionOut] = []

    model_config = {"from_attributes": True}

class CategoryOut(BaseModel):
    id: str
    name_ko: str
    name_en: str
    display_order: int
    is_visible: bool
    image_url: str | None

    model_config = {"from_attributes": True}

# GET /api/menu 응답 최상위 구조
class MenuResponse(BaseModel):
    categories: list[CategoryOut]
    menu_items: dict[str, list[MenuItemOut]]  # category_slug → items
```

#### `backend/schemas/cart_schemas.py`

```python
from pydantic import BaseModel
from decimal import Decimal

class SelectedOption(BaseModel):
    option_id: str
    name: str

class CartItemIn(BaseModel):
    menu_item_id: str
    quantity: int = 1
    selected_options: list[SelectedOption] = []
    special_note: str | None = None

class CartItemOut(BaseModel):
    cart_item_id: str
    menu_item_id: str
    name_ko: str
    quantity: int
    unit_price: Decimal
    selected_options: list[SelectedOption]
    special_note: str | None

class CartItemUpdateIn(BaseModel):
    quantity: int | None = None
    selected_options: list[SelectedOption] | None = None
    special_note: str | None = None

class CartOut(BaseModel):
    cart_id: str
    session_id: str
    items: list[CartItemOut]
    total: Decimal
```

#### `backend/schemas/order_schemas.py`

```python
from pydantic import BaseModel
from decimal import Decimal

class OrderIn(BaseModel):
    session_id: str
    order_type: str = "TAKE_OUT"   # EAT_IN | TAKE_OUT
    phone: str | None = None        # 포인트 적립용 (비회원도 전화번호로 적립 가능)
    points_to_use: int = 0
    coupon_code: str | None = None

class OrderItemOut(BaseModel):
    menu_item_id: str
    name_ko: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    selected_options: list
    special_note: str | None

class OrderOut(BaseModel):
    order_id: str
    order_number: str
    order_type: str
    subtotal: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    points_used: int
    points_earned: int
    items: list[OrderItemOut]
```

#### `backend/schemas/payment_schemas.py`

```python
from pydantic import BaseModel
from decimal import Decimal

class PaymentIn(BaseModel):
    order_id: str
    method: str            # CARD | SAMSUNG_PAY | QR_PAY | CASH
    amount: Decimal
    pg_transaction_id: str | None = None
    pg_provider: str | None = None

class PaymentOut(BaseModel):
    payment_id: str
    order_id: str
    method: str
    amount: Decimal
    status: str
    paid_at: str | None
```

#### `backend/schemas/user_schemas.py`

```python
from pydantic import BaseModel

class UserPointsOut(BaseModel):
    user_id: str
    phone_number: str
    current_points: int
    tier: str | None  # BASIC | SILVER | GOLD

class CouponOut(BaseModel):
    user_coupon_id: str
    coupon_code: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    is_used: bool
    valid_until: str | None
```

---

### 2단계: dao/ (DB 접근 계층)

**원칙:** 모든 함수는 `async def`. SQL 로직은 DAO에만. API 라우터에서 직접 쿼리 금지.

#### `backend/dao/menu_dao.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.models import Category, MenuItem

async def get_all_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.is_visible == True)
        .order_by(Category.display_order)
    )
    return result.scalars().all()

async def get_menu_items_by_category(
    db: AsyncSession, category_id: str
) -> list[MenuItem]:
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.category_id == category_id)
        .where(MenuItem.is_available == True)
        .options(selectinload(MenuItem.options))
        .order_by(MenuItem.display_order)
    )
    return result.scalars().all()

async def get_menu_item_by_id(db: AsyncSession, item_id: str) -> MenuItem | None:
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.id == item_id)
        .options(selectinload(MenuItem.options))
    )
    return result.scalar_one_or_none()

async def get_popular_items(db: AsyncSession) -> list[MenuItem]:
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.is_popular == True)
        .where(MenuItem.is_available == True)
        .options(selectinload(MenuItem.options))
    )
    return result.scalars().all()
```

#### `backend/dao/cart_dao.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from decimal import Decimal
from core.models import Cart, CartItem, MenuItem

async def get_or_create_cart(db: AsyncSession, session_id: str) -> Cart:
    result = await db.execute(
        select(Cart)
        .where(Cart.session_id == session_id)
        .where(Cart.status == "ACTIVE")
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(session_id=session_id)
        db.add(cart)
        await db.flush()
    return cart

async def get_cart_with_items(db: AsyncSession, session_id: str) -> Cart | None:
    result = await db.execute(
        select(Cart)
        .where(Cart.session_id == session_id)
        .where(Cart.status == "ACTIVE")
        .options(selectinload(Cart.items).selectinload(CartItem.menu_item))
    )
    return result.scalar_one_or_none()

async def add_cart_item(
    db: AsyncSession,
    cart_id: str,
    menu_item_id: str,
    quantity: int,
    unit_price: Decimal,
    selected_options: list,
    special_note: str | None,
) -> CartItem:
    item = CartItem(
        cart_id=cart_id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        unit_price=unit_price,
        selected_options=selected_options,
        special_note=special_note,
    )
    db.add(item)
    await db.flush()
    return item

async def update_cart_item(
    db: AsyncSession,
    cart_item_id: str,
    **kwargs,
) -> CartItem | None:
    result = await db.execute(
        select(CartItem).where(CartItem.id == cart_item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(item, key, value)
    await db.flush()
    return item

async def delete_cart_item(db: AsyncSession, cart_item_id: str) -> bool:
    result = await db.execute(
        select(CartItem).where(CartItem.id == cart_item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        return False
    await db.delete(item)
    return True

async def clear_cart(db: AsyncSession, session_id: str) -> None:
    cart = await get_cart_with_items(db, session_id)
    if cart:
        for item in cart.items:
            await db.delete(item)
```

#### `backend/dao/order_dao.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from decimal import Decimal
from core.models import Order, OrderItem, Cart

async def create_order_from_cart(
    db: AsyncSession,
    cart_id: str,
    order_type: str,
    subtotal: Decimal,
    discount_amount: Decimal,
    final_amount: Decimal,
    points_used: int,
    points_earned: int,
    user_id: str | None = None,
) -> Order:
    # 주문번호: 당일 순번 (1~999)
    count_result = await db.execute(select(func.count(Order.id)))
    order_num = (count_result.scalar() or 0) + 1

    order = Order(
        user_id=user_id,
        cart_id=cart_id,
        order_number=str(order_num),
        order_type=order_type,
        subtotal=subtotal,
        discount_amount=discount_amount,
        final_amount=final_amount,
        points_used=points_used,
        points_earned=points_earned,
    )
    db.add(order)
    await db.flush()
    return order

async def create_order_items_from_cart_items(
    db: AsyncSession, order_id: str, cart_items: list
) -> None:
    for ci in cart_items:
        total = ci.unit_price * ci.quantity
        db.add(OrderItem(
            order_id=order_id,
            menu_item_id=ci.menu_item_id,
            quantity=ci.quantity,
            unit_price=ci.unit_price,
            total_price=total,
            selected_options=ci.selected_options,
            special_note=ci.special_note,
        ))

async def get_order_by_id(db: AsyncSession, order_id: str) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    return result.scalar_one_or_none()
```

#### `backend/dao/payment_dao.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime
from core.models import Payment

async def create_payment(
    db: AsyncSession,
    order_id: str,
    method: str,
    amount: Decimal,
    pg_transaction_id: str | None = None,
    pg_provider: str | None = None,
) -> Payment:
    payment = Payment(
        order_id=order_id,
        method=method,
        amount=amount,
        pg_transaction_id=pg_transaction_id,
        pg_provider=pg_provider,
        status="SUCCESS",
        paid_at=datetime.utcnow(),
    )
    db.add(payment)
    await db.flush()
    return payment
```

#### `backend/dao/user_dao.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import User, Membership, UserCoupon, Coupon

async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(
        select(User).where(User.phone_number == phone)
    )
    return result.scalar_one_or_none()

async def get_membership(db: AsyncSession, user_id: str) -> Membership | None:
    result = await db.execute(
        select(Membership).where(Membership.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def get_unused_coupons(db: AsyncSession, user_id: str) -> list[UserCoupon]:
    result = await db.execute(
        select(UserCoupon)
        .where(UserCoupon.user_id == user_id)
        .where(UserCoupon.is_used == False)
    )
    return result.scalars().all()

async def get_coupon_by_code(db: AsyncSession, code: str) -> Coupon | None:
    result = await db.execute(
        select(Coupon)
        .where(Coupon.code == code)
        .where(Coupon.is_active == True)
    )
    return result.scalar_one_or_none()
```

---

### 3단계: api/ (FastAPI 라우터)

#### `backend/api/menu.py`

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from dao.menu_dao import get_all_categories, get_menu_items_by_category
from schemas.menu_schemas import CategoryOut, MenuItemOut, MenuResponse

router = APIRouter(prefix="/api/menu", tags=["menu"])

@router.get("", response_model=MenuResponse)
async def get_menu(
    locale: str = Query(default="ko", pattern="^(ko|en|zh|ja)$"),
    db: AsyncSession = Depends(get_db),
):
    categories = await get_all_categories(db)
    menu_items: dict[str, list] = {}
    for cat in categories:
        items = await get_menu_items_by_category(db, cat.id)
        # locale에 따라 name 필드 선택 (ko/en만 지원, zh/ja는 ko 폴백)
        menu_items[cat.name_en.lower()] = [MenuItemOut.model_validate(i) for i in items]

    return MenuResponse(
        categories=[CategoryOut.model_validate(c) for c in categories],
        menu_items=menu_items,
    )

@router.get("/items/{item_id}", response_model=MenuItemOut)
async def get_menu_item(item_id: str, db: AsyncSession = Depends(get_db)):
    from dao.menu_dao import get_menu_item_by_id
    from fastapi import HTTPException
    item = await get_menu_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다")
    return MenuItemOut.model_validate(item)
```

#### `backend/api/cart.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from core.db import get_db
from dao.cart_dao import (
    get_or_create_cart, get_cart_with_items,
    add_cart_item, update_cart_item, delete_cart_item, clear_cart
)
from dao.menu_dao import get_menu_item_by_id
from schemas.cart_schemas import CartItemIn, CartItemOut, CartItemUpdateIn, CartOut

router = APIRouter(prefix="/api/cart", tags=["cart"])

@router.get("/{session_id}", response_model=CartOut)
async def get_cart(session_id: str, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_with_items(db, session_id)
    if cart is None:
        # 빈 장바구니 반환 (에러 X)
        return CartOut(cart_id="", session_id=session_id, items=[], total=Decimal("0"))

    items_out = []
    total = Decimal("0")
    for ci in cart.items:
        items_out.append(CartItemOut(
            cart_item_id=ci.id,
            menu_item_id=ci.menu_item_id,
            name_ko=ci.menu_item.name_ko,
            quantity=ci.quantity,
            unit_price=ci.unit_price,
            selected_options=ci.selected_options or [],
            special_note=ci.special_note,
        ))
        total += ci.unit_price * ci.quantity
    return CartOut(cart_id=cart.id, session_id=session_id, items=items_out, total=total)

@router.post("/{session_id}/items")
async def add_item_to_cart(
    session_id: str, body: CartItemIn, db: AsyncSession = Depends(get_db)
):
    menu_item = await get_menu_item_by_id(db, body.menu_item_id)
    if menu_item is None:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다")
    if not menu_item.is_available:
        raise HTTPException(status_code=409, detail="현재 주문 불가능한 메뉴입니다")

    # 옵션 추가금 계산
    option_extra = Decimal("0")
    for sel in body.selected_options:
        opt = next((o for o in menu_item.options if o.id == sel.option_id), None)
        if opt:
            option_extra += opt.additional_price

    unit_price = menu_item.base_price + option_extra

    cart = await get_or_create_cart(db, session_id)
    cart_item = await add_cart_item(
        db, cart.id, body.menu_item_id, body.quantity,
        unit_price, [o.model_dump() for o in body.selected_options], body.special_note
    )
    await db.commit()
    return {"cart_item_id": cart_item.id, "cart_id": cart.id}

@router.patch("/{session_id}/items/{cart_item_id}")
async def update_item(
    session_id: str, cart_item_id: str, body: CartItemUpdateIn,
    db: AsyncSession = Depends(get_db)
):
    item = await update_cart_item(
        db, cart_item_id,
        quantity=body.quantity,
        selected_options=[o.model_dump() for o in body.selected_options] if body.selected_options else None,
        special_note=body.special_note,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="장바구니 항목을 찾을 수 없습니다")
    await db.commit()
    return {"ok": True}

@router.delete("/{session_id}/items/{cart_item_id}")
async def remove_item(
    session_id: str, cart_item_id: str, db: AsyncSession = Depends(get_db)
):
    deleted = await delete_cart_item(db, cart_item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="장바구니 항목을 찾을 수 없습니다")
    await db.commit()
    return {"ok": True}

@router.delete("/{session_id}")
async def clear_cart_endpoint(session_id: str, db: AsyncSession = Depends(get_db)):
    await clear_cart(db, session_id)
    await db.commit()
    return {"ok": True}
```

#### `backend/api/order.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from core.db import get_db
from dao.cart_dao import get_cart_with_items
from dao.order_dao import create_order_from_cart, create_order_items_from_cart_items, get_order_by_id
from schemas.order_schemas import OrderIn, OrderOut

router = APIRouter(prefix="/api/orders", tags=["order"])

@router.post("", response_model=OrderOut)
async def create_order(body: OrderIn, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_with_items(db, body.session_id)
    if cart is None or not cart.items:
        raise HTTPException(status_code=400, detail="장바구니가 비어있습니다")

    subtotal = sum(ci.unit_price * ci.quantity for ci in cart.items)
    discount_amount = Decimal("0")
    # TODO: 쿠폰 적용 로직 추가 (coupon_code 검증 → discount 계산)
    final_amount = subtotal - discount_amount - (body.points_to_use or 0)
    points_earned = int(final_amount * Decimal("0.05"))  # 결제금액 5% 적립

    order = await create_order_from_cart(
        db, cart.id, body.order_type, subtotal,
        discount_amount, final_amount, body.points_to_use, points_earned
    )
    await create_order_items_from_cart_items(db, order.id, cart.items)

    # 장바구니 상태 COMPLETED로 변경
    cart.status = "COMPLETED"
    await db.commit()

    order_with_items = await get_order_by_id(db, order.id)
    return OrderOut(
        order_id=order.id,
        order_number=order.order_number,
        order_type=order.order_type,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        final_amount=order.final_amount,
        points_used=order.points_used,
        points_earned=order.points_earned,
        items=[],  # 필요 시 items 직렬화 추가
    )

@router.get("/{order_id}")
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
    return {"order_id": order.id, "order_number": order.order_number, "status": "completed"}
```

#### `backend/api/user.py` (포인트/쿠폰 조회)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from dao.user_dao import get_user_by_phone, get_membership, get_unused_coupons
from schemas.user_schemas import UserPointsOut, CouponOut

router = APIRouter(prefix="/api/user", tags=["user"])

@router.get("/points/{phone}", response_model=UserPointsOut)
async def get_user_points(phone: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_phone(db, phone)
    if user is None:
        raise HTTPException(status_code=404, detail="등록된 회원이 아닙니다")
    membership = await get_membership(db, user.id)
    return UserPointsOut(
        user_id=user.id,
        phone_number=user.phone_number,
        current_points=user.current_points,
        tier=membership.tier if membership else None,
    )

@router.get("/{user_id}/coupons", response_model=list[CouponOut])
async def get_user_coupons(user_id: str, db: AsyncSession = Depends(get_db)):
    user_coupons = await get_unused_coupons(db, user_id)
    result = []
    for uc in user_coupons:
        result.append(CouponOut(
            user_coupon_id=uc.id,
            coupon_code=uc.coupon.code if uc.coupon else "",
            discount_type=uc.coupon.discount_type if uc.coupon else "",
            discount_value=float(uc.coupon.discount_value) if uc.coupon else 0,
            min_order_amount=float(uc.coupon.min_order_amount) if uc.coupon else 0,
            is_used=uc.is_used,
            valid_until=str(uc.coupon.valid_until) if uc.coupon and uc.coupon.valid_until else None,
        ))
    return result
```

---

### 4단계: main.py 라우터 등록

`backend/main.py`에 아래 코드를 추가한다 (기존 llm/stt/tts 라우터 등록 아래에).

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

---

## 컨벤션

1. 모든 DAO 함수는 `async def`, 세션 파라미터는 마지막 인자
2. `await db.flush()` 후 `await db.commit()`는 반드시 라우터에서 호출 (DAO에서 commit 금지)
3. 에러 응답은 `raise HTTPException(status_code=..., detail="한국어 메시지")`
4. 응답 모델은 반드시 `response_model=` 파라미터로 명시

---

## 완료 기준

- [ ] `uvicorn main:app` 기동 후 `GET http://localhost:8000/api/menu` 가 JSON 반환
- [ ] `POST /api/cart/{session_id}/items` → `GET /api/cart/{session_id}` 장바구니에 항목 확인
- [ ] `POST /api/orders` → orders 테이블에 레코드 생성 확인 (DB 직접 조회)
- [ ] 프론트엔드 `.env`에 `VITE_API_URL=http://localhost:8000` 설정 후 메뉴 화면 동작
- [ ] FastAPI `/docs` 페이지에서 전 엔드포인트 스웨거 확인 가능
