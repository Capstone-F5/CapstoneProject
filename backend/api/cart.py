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