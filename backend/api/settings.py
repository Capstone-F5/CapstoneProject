from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.kiosk_settings import (
    DEFAULT_KIOSK_SETTINGS,
    get_kiosk_settings,
    reset_kiosk_settings,
    update_kiosk_settings,
)
from dao.settings_dao import get_active_start_screen_images
from schemas.settings_schemas import StartScreenImageOut

router = APIRouter(prefix="/api/settings", tags=["settings"])

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


@router.get("/start-screen-images", response_model=list[StartScreenImageOut])
async def list_start_screen_images(db: AsyncSession = Depends(get_session)):
    images = await get_active_start_screen_images(db)
    return [StartScreenImageOut.model_validate(i) for i in images]


@router.get("/kiosk")
async def get_kiosk_dev_settings() -> dict[str, Any]:
    """키오스크 개발자 설정(마이크 감도 · 접근 감지) 현재값 및 기본값 반환."""
    return {
        "settings": get_kiosk_settings(),
        "defaults": DEFAULT_KIOSK_SETTINGS,
    }


@router.put("/kiosk")
async def put_kiosk_dev_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """키오스크 개발자 설정을 즉시 갱신하고 영구 저장한다."""
    updated = update_kiosk_settings(payload)
    return {
        "settings": updated,
        "defaults": DEFAULT_KIOSK_SETTINGS,
    }


@router.post("/kiosk/reset")
async def reset_kiosk_dev_settings() -> dict[str, Any]:
    """키오스크 개발자 설정을 기본값으로 초기화한다."""
    reset = reset_kiosk_settings()
    return {
        "settings": reset,
        "defaults": DEFAULT_KIOSK_SETTINGS,
    }


def _tail_lines(path: Path, limit: int = 30) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-limit:]
    except Exception:
        return []


@router.get("/kiosk/logs")
async def get_kiosk_diagnostic_logs(limit: int = Query(30, ge=5, le=100)) -> dict[str, list[str]]:
    """최근 접근 감지 로그(approach.log)와 음성 게이트/지연 진단 로그(voice_timing.log)를 반환."""
    return {
        "approach": _tail_lines(_LOG_DIR / "approach.log", limit),
        "voice": _tail_lines(_LOG_DIR / "voice_timing.log", limit),
    }
