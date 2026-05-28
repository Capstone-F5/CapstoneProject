"""
SQLAlchemy 비동기 엔진 / 세션 / Base.
DB URL 은 .env 의 DATABASE_URL (기본: sqlite+aiosqlite:///./kiosk.db)
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./kiosk.db")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    """FastAPI Depends 용 세션 컨텍스트."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """앱 시작 시 테이블 생성 + 메뉴 시드."""
    from . import models  # noqa: F401 (모델 등록)
    from .seed import seed_menu

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        await seed_menu(session)
