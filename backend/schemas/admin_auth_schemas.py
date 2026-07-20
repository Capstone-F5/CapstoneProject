from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 초 단위


class AdminMeOut(BaseModel):
    id: str
    username: str
    display_name: str
    role: str  # OWNER | STAFF
