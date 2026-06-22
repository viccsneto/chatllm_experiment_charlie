from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=4, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    user_id: int


class UserOut(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}