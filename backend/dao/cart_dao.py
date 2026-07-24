from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from decimal import Decimal
from core.models import Cart, CartItem, MenuItem, MenuOption

async def get_or_create_cart(db: AsyncSession, session_id: str) -> Cart:
    result = await db.execute(
        select(Cart)
        .where(Cart.session_id == session_id)
        .where(Cart.status == "ACTIVE")
    )
    cart = result.scalar_one_or_none()
    if cart is not None:
        return cart

    # 한 발화에서 여러 add_item 툴이 동시에 호출되면 이 지점에서 동시에 "없음"을 보고
    # 각자 새 카트를 만들려는 경쟁 상태가 발생할 수 있다. DB의 uq_carts_active_session
    # 유니크 제약이 두 번째 이후 INSERT를 막아주므로, 그 경우 롤백 후 먼저 커밋된
    # 카트를 다시 조회해 반환한다.
    cart = Cart(session_id=session_id)
    db.add(cart)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(Cart)
            .where(Cart.session_id == session_id)
            .where(Cart.status == "ACTIVE")
        )
        cart = result.scalar_one()
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

async def get_cart_item_with_menu(db: AsyncSession, cart_item_id: str) -> CartItem | None:
    result = await db.execute(
        select(CartItem)
        .where(CartItem.id == cart_item_id)
        .options(selectinload(CartItem.menu_item).selectinload(MenuItem.options))
    )
    return result.scalar_one_or_none()


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