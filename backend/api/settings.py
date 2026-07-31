from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_session
from dao.settings_dao import get_active_start_screen_images
from schemas.settings_schemas import StartScreenImageOut

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/start-screen-images", response_model=list[StartScreenImageOut])
async def list_start_screen_images(db: AsyncSession = Depends(get_session)):
    images = await get_active_start_screen_images(db)
    return [StartScreenImageOut.model_validate(i) for i in images]
