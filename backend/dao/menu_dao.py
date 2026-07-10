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