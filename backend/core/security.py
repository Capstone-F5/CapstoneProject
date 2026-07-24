"""
관리자 인증 — 비밀번호 해시 + JWT 발급/검증.
다른 모듈은 이 파일의 get_current_admin/require_owner만 import해서 쓰면 된다.
"""
import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/auth/login")

_SECRET = os.getenv("ADMIN_JWT_SECRET", "dev-only-insecure-secret")
_EXPIRE_MIN = int(os.getenv("ADMIN_JWT_EXPIRE_MINUTES", "480"))


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def create_access_token(admin_id: str, role: str) -> tuple[str, int]:
    expire = datetime.utcnow() + timedelta(minutes=_EXPIRE_MIN)
    payload = {"sub": admin_id, "role": role, "exp": expire}
    token = jwt.encode(payload, _SECRET, algorithm="HS256")
    return token, _EXPIRE_MIN * 60


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> dict:
    """반환값: {"id": admin_id, "role": role}."""
    try:
        payload = jwt.decode(token, _SECRET, algorithms=["HS256"])
        return {"id": payload["sub"], "role": payload["role"]}
    except JWTError:
        raise HTTPException(401, "인증 정보가 유효하지 않습니다. 다시 로그인해 주세요.")


async def require_owner(admin: dict = Depends(get_current_admin)) -> dict:
    if admin["role"] != "OWNER":
        raise HTTPException(403, "관리자(OWNER) 권한이 필요합니다.")
    return admin
