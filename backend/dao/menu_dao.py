from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.models import Category, MenuItem, MenuOption, MenuItemAllergen, Order, OrderItem

# 메뉴 조회 시 항상 함께 로드해야 하는 관계 — 지연 로딩 시 async 컨텍스트에서 오류가 나므로
# (allergens 프로퍼티가 allergen_links를 동기적으로 읽음) 매번 selectinload로 미리 채운다.
_MENU_ITEM_LOAD_OPTS = (
    selectinload(MenuItem.options),
    selectinload(MenuItem.allergen_links).selectinload(MenuItemAllergen.allergen),
)

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
        .options(*_MENU_ITEM_LOAD_OPTS)
        .order_by(MenuItem.display_order)
    )
    return result.scalars().all()

async def get_menu_item_by_id(db: AsyncSession, item_id: str) -> MenuItem | None:
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.id == item_id)
        .options(*_MENU_ITEM_LOAD_OPTS)
    )
    return result.scalar_one_or_none()

async def get_popular_items(db: AsyncSession) -> list[MenuItem]:
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.is_popular == True)
        .where(MenuItem.is_available == True)
        .options(*_MENU_ITEM_LOAD_OPTS)
    )
    return result.scalars().all()


# --- 관리자용 CRUD (Module B) ------------------------------------------------

_ACTIVE_ORDER_STATUSES = ("RECEIVED", "COOKING", "READY")


async def get_all_categories_admin(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.display_order))
    return result.scalars().all()


async def get_menu_items_by_category_admin(
    db: AsyncSession, category_id: str
) -> list[MenuItem]:
    """관리자용 - 품절(is_available=False) 메뉴도 포함"""
    result = await db.execute(
        select(MenuItem)
        .where(MenuItem.category_id == category_id)
        .options(*_MENU_ITEM_LOAD_OPTS)
        .order_by(MenuItem.display_order)
    )
    return result.scalars().all()


async def get_category_by_id(db: AsyncSession, category_id: str) -> Category | None:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, data: dict) -> Category:
    category = Category(**data)
    db.add(category)
    await db.flush()
    return category


async def update_category(db: AsyncSession, category: Category, data: dict) -> Category:
    for key, value in data.items():
        setattr(category, key, value)
    await db.flush()
    return category


async def category_has_menu_items(db: AsyncSession, category_id: str) -> bool:
    result = await db.execute(
        select(MenuItem.id).where(MenuItem.category_id == category_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def delete_category(db: AsyncSession, category: Category) -> None:
    await db.delete(category)
    await db.flush()


async def get_all_menu_items_admin(db: AsyncSession) -> list[MenuItem]:
    result = await db.execute(
        select(MenuItem)
        .options(*_MENU_ITEM_LOAD_OPTS)
        .order_by(MenuItem.category_id, MenuItem.display_order)
    )
    return result.scalars().all()


async def create_menu_item(db: AsyncSession, data: dict) -> MenuItem:
    item = MenuItem(**data)
    db.add(item)
    await db.flush()
    return item


async def update_menu_item(db: AsyncSession, item: MenuItem, data: dict) -> MenuItem:
    for key, value in data.items():
        setattr(item, key, value)
    await db.flush()
    return item


async def is_menu_item_in_active_order(db: AsyncSession, item_id: str) -> bool:
    """진행 중(접수/조리/픽업대기)인 주문에 이 메뉴가 포함되어 있으면 True."""
    result = await db.execute(
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.menu_item_id == item_id)
        .where(Order.status.in_(_ACTIVE_ORDER_STATUSES))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def soft_delete_menu_item(db: AsyncSession, item: MenuItem) -> None:
    item.is_available = False
    await db.flush()


async def hard_delete_menu_item(db: AsyncSession, item: MenuItem) -> None:
    await db.delete(item)
    await db.flush()


async def get_menu_option_by_id(db: AsyncSession, option_id: str) -> MenuOption | None:
    result = await db.execute(select(MenuOption).where(MenuOption.id == option_id))
    return result.scalar_one_or_none()


async def create_menu_option(db: AsyncSession, menu_item_id: str, data: dict) -> MenuOption:
    option = MenuOption(menu_item_id=menu_item_id, **data)
    db.add(option)
    await db.flush()
    return option


async def update_menu_option(db: AsyncSession, option: MenuOption, data: dict) -> MenuOption:
    for key, value in data.items():
        setattr(option, key, value)
    await db.flush()
    return option


async def delete_menu_option(db: AsyncSession, option: MenuOption) -> None:
    await db.delete(option)
    await db.flush()