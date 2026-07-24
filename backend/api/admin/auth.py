from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.security import (
    create_access_token,
    get_current_admin,
    verify_password,
)
from dao.admin_dao import get_admin_by_id, get_admin_by_username, touch_last_login
from schemas.admin_auth_schemas import AdminMeOut, LoginIn, LoginOut

# 로그인 자체는 인증 없이 호출해야 하므로 이 라우터엔 공통 인증 dependency를 걸지 않는다.
router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=LoginOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_session)):
    admin = await get_admin_by_username(db, payload.username)
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다")
    if not admin.is_active:
        raise HTTPException(401, "비활성화된 계정입니다")

    access_token, expires_in = create_access_token(admin.id, admin.role)
    await touch_last_login(db, admin.id)
    await db.commit()

    return LoginOut(access_token=access_token, expires_in=expires_in)


@router.post("/logout")
async def logout():
    return {"ok": True}


@router.get("/me", response_model=AdminMeOut)
async def get_me(
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
):
    record = await get_admin_by_id(db, admin["id"])
    if record is None:
        raise HTTPException(401, "인증 정보가 유효하지 않습니다. 다시 로그인해 주세요.")
    return AdminMeOut(
        id=record.id,
        username=record.username,
        display_name=record.display_name,
        role=record.role,
    )
