import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_modules.llm.rag import invalidate_cache
from core.db import get_session
from core.security import get_current_admin
from dao import menu_dao
from schemas.menu_schemas import (
    CategoryIn,
    CategoryOut,
    CategoryPatchIn,
    MenuItemIn,
    MenuItemOut,
    MenuItemPatchIn,
    MenuOptionIn,
    MenuOptionOut,
    MenuOptionPatchIn,
)

_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "static", "uploads", "menu",
)
_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-menu"],
    dependencies=[Depends(get_current_admin)],
)


# --- 이미지 업로드 -----------------------------------------------------------
@router.post("/upload/image")
async def upload_menu_image(file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(400, "jpg, png, webp, gif 이미지만 업로드 가능합니다")
    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(400, "파일 크기는 5MB 이하여야 합니다")
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    ext = (file.filename or "img").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        ext = "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    with open(os.path.join(_UPLOAD_DIR, filename), "wb") as f:
        f.write(content)
    return {"url": f"/static/uploads/menu/{filename}"}


# --- 카테고리 ---------------------------------------------------------------
@router.post("/categories", response_model=CategoryOut)
async def create_category(payload: CategoryIn, db: AsyncSession = Depends(get_session)):
    category = await menu_dao.create_category(db, payload.model_dump())
    await db.commit()
    return category


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: str, payload: CategoryPatchIn, db: AsyncSession = Depends(get_session)
):
    category = await menu_dao.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(404, "카테고리를 찾을 수 없습니다")
    category = await menu_dao.update_category(
        db, category, payload.model_dump(exclude_unset=True)
    )
    await db.commit()
    return category


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, db: AsyncSession = Depends(get_session)):
    category = await menu_dao.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(404, "카테고리를 찾을 수 없습니다")
    if await menu_dao.category_has_menu_items(db, category_id):
        raise HTTPException(409, "하위 메뉴가 있는 카테고리는 삭제할 수 없습니다")

    try:
        await menu_dao.delete_category(db, category)
        await db.commit()
    except IntegrityError:
        # 할인(Discount) 등 다른 테이블이 이 카테고리를 참조 중 — 하드 삭제 대신 비노출 처리.
        await db.rollback()
        category = await menu_dao.get_category_by_id(db, category_id)
        await menu_dao.update_category(db, category, {"is_visible": False})
        await db.commit()
        raise HTTPException(
            409, "다른 데이터가 참조 중인 카테고리라 삭제 대신 비노출 처리되었습니다"
        )

    return {"ok": True}


# --- 메뉴 ------------------------------------------------------------------
@router.post("/menu/items", response_model=MenuItemOut)
async def create_menu_item(payload: MenuItemIn, db: AsyncSession = Depends(get_session)):
    item = await menu_dao.create_menu_item(db, payload.model_dump())
    await db.commit()
    invalidate_cache()
    return item


@router.patch("/menu/items/{item_id}", response_model=MenuItemOut)
async def update_menu_item(
    item_id: str, payload: MenuItemPatchIn, db: AsyncSession = Depends(get_session)
):
    item = await menu_dao.get_menu_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(404, "메뉴를 찾을 수 없습니다")
    item = await menu_dao.update_menu_item(db, item, payload.model_dump(exclude_unset=True))
    await db.commit()
    invalidate_cache()
    return item


@router.delete("/menu/items/{item_id}")
async def delete_menu_item(item_id: str, db: AsyncSession = Depends(get_session)):
    item = await menu_dao.get_menu_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(404, "메뉴를 찾을 수 없습니다")

    if await menu_dao.is_menu_item_in_active_order(db, item_id):
        await menu_dao.soft_delete_menu_item(db, item)
        await db.commit()
        invalidate_cache()
        raise HTTPException(
            409, "진행 중인 주문에 포함된 메뉴라 삭제 대신 품절 처리되었습니다"
        )

    try:
        await menu_dao.hard_delete_menu_item(db, item)
        await db.commit()
    except IntegrityError:
        # 과거 주문/장바구니 등 다른 테이블이 이 메뉴를 참조 중 — 하드 삭제 대신 품절 처리.
        await db.rollback()
        item = await menu_dao.get_menu_item_by_id(db, item_id)
        await menu_dao.soft_delete_menu_item(db, item)
        await db.commit()
        invalidate_cache()
        raise HTTPException(
            409, "주문 이력이 있는 메뉴라 삭제 대신 품절 처리되었습니다"
        )

    invalidate_cache()
    return {"ok": True}


# --- 메뉴 옵션 ---------------------------------------------------------------
@router.post("/menu/items/{item_id}/options", response_model=MenuOptionOut)
async def create_menu_option(
    item_id: str, payload: MenuOptionIn, db: AsyncSession = Depends(get_session)
):
    item = await menu_dao.get_menu_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(404, "메뉴를 찾을 수 없습니다")
    option = await menu_dao.create_menu_option(db, item_id, payload.model_dump())
    await db.commit()
    invalidate_cache()
    return option


@router.patch("/menu/items/{item_id}/options/{option_id}", response_model=MenuOptionOut)
async def update_menu_option(
    item_id: str,
    option_id: str,
    payload: MenuOptionPatchIn,
    db: AsyncSession = Depends(get_session),
):
    option = await menu_dao.get_menu_option_by_id(db, option_id)
    if option is None or option.menu_item_id != item_id:
        raise HTTPException(404, "옵션을 찾을 수 없습니다")
    option = await menu_dao.update_menu_option(
        db, option, payload.model_dump(exclude_unset=True)
    )
    await db.commit()
    invalidate_cache()
    return option


@router.delete("/menu/items/{item_id}/options/{option_id}")
async def delete_menu_option(
    item_id: str, option_id: str, db: AsyncSession = Depends(get_session)
):
    option = await menu_dao.get_menu_option_by_id(db, option_id)
    if option is None or option.menu_item_id != item_id:
        raise HTTPException(404, "옵션을 찾을 수 없습니다")
    await menu_dao.delete_menu_option(db, option)
    await db.commit()
    invalidate_cache()
    return {"ok": True}
