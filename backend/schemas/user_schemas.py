from pydantic import BaseModel
from typing import Optional


class UserPointsResponse(BaseModel):
    phone: str
    points: int
    membership_grade: Optional[str] = None

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    phone: str
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    phone: str
    name: Optional[str] = None
    points: int = 0

    class Config:
        from_attributes = True
