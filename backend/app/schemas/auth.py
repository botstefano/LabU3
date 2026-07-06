import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=6)
    rol: UserRole = UserRole.VENDEDOR


class UserResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    email: EmailStr
    rol: UserRole
    activo: bool

    model_config = {"from_attributes": True}


TokenResponse.model_rebuild()
