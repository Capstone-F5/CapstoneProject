"""
관리자 계정 부트스트랩.
앱 시작 시 admin_users 테이블이 비어 있으면 .env의 ADMIN_BOOTSTRAP_USERNAME/PASSWORD로
OWNER 계정 1개를 자동 생성한다(최초 1회, 이후엔 계정이 있으므로 아무 것도 하지 않음).
"""
from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession

from dao.admin_dao import count_admins, create_admin
from .security import hash_password


async def seed_admin(db: AsyncSession) -> None:
    if await count_admins(db) > 0:
        return

    username = os.getenv("ADMIN_BOOTSTRAP_USERNAME", "admin")
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "change-me-on-first-login")

    await create_admin(
        db,
        username=username,
        password_hash=hash_password(password),
        display_name="관리자",
        role="OWNER",
    )
    await db.commit()
