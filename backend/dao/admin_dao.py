from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import AdminUser


async def get_admin_by_username(db: AsyncSession, username: str) -> AdminUser | None:
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == username)
    )
    return result.scalar_one_or_none()


async def get_admin_by_id(db: AsyncSession, admin_id: str) -> AdminUser | None:
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == admin_id)
    )
    return result.scalar_one_or_none()


async def count_admins(db: AsyncSession) -> int:
    result = await db.execute(select(AdminUser))
    return len(result.scalars().all())


async def create_admin(
    db: AsyncSession, username: str, password_hash: str, display_name: str, role: str
) -> AdminUser:
    admin = AdminUser(
        username=username,
        password_hash=password_hash,
        display_name=display_name,
        role=role,
    )
    db.add(admin)
    await db.flush()
    return admin


async def touch_last_login(db: AsyncSession, admin_id: str) -> None:
    admin = await get_admin_by_id(db, admin_id)
    if admin is not None:
        admin.last_login_at = datetime.utcnow()
        await db.flush()
