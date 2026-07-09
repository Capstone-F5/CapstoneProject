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