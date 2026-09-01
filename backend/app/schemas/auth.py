from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from backend.app.models.user import UserRole
from backend.app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1)
    role: UserRole = UserRole.PROPERTY_MANAGER


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
