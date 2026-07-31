from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import StartScreenImage


async def get_active_start_screen_images(db: AsyncSession) -> list[StartScreenImage]:
    result = await db.execute(
        select(StartScreenImage)
        .where(StartScreenImage.is_active == True)
        .order_by(StartScreenImage.display_order)
    )
    return result.scalars().all()
