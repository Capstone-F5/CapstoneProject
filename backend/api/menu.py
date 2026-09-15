from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_session
from dao.menu_dao import get_all_categories, get_menu_items_by_category
from dao import discount_dao
from core.pricing import calculate_menu_price
from schemas.menu_schemas import CategoryOut, MenuItemOut, MenuResponse

router = APIRouter(prefix="/api/menu", tags=["menu"])

@router.get("", response_model=MenuResponse)
async def get_menu(
    locale: str = Query(default="ko", pattern="^(ko|en|zh|ja)$"),
    db: AsyncSession = Depends(get_session),
):
    categories = await get_all_categories(db)
    discounts = await discount_dao.get_active_discounts(db)
    menu_items: dict[str, list] = {}
    for cat in categories:
        items = await get_menu_items_by_category(db, cat.id)
        # locale에 따라 name 필드 선택 (ko/en만 지원, zh/ja는 ko 폴백)
        menu_items[cat.name_en.lower()] = []
        for item in items:
            price = calculate_menu_price(item, discounts)
            menu_items[cat.name_en.lower()].append(
                MenuItemOut.model_validate(item).model_copy(update=price)
            )

    return MenuResponse(
        categories=[CategoryOut.model_validate(c) for c in categories],
        menu_items=menu_items,
    )

@router.get("/items/{item_id}", response_model=MenuItemOut)
async def get_menu_item(item_id: str, db: AsyncSession = Depends(get_session)):
    from dao.menu_dao import get_menu_item_by_id
    from fastapi import HTTPException
    item = await get_menu_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다")
    discounts = await discount_dao.get_active_discounts(db)
    return MenuItemOut.model_validate(item).model_copy(
        update=calculate_menu_price(item, discounts)
    )