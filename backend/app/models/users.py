from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

ALLOWED_ROLES = ("ADMIN", "MANAGER", "STAFF")
MIN_PASSWORD_LENGTH = 8


class UserListItem(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserDetail(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)
    role: str = "STAFF"
    is_active: bool = True

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ALLOWED_ROLES:
            raise ValueError(f"Rôle invalide. Valeurs autorisées: {', '.join(ALLOWED_ROLES)}")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
        return v


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=MIN_PASSWORD_LENGTH)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_ROLES:
            raise ValueError(f"Rôle invalide. Valeurs autorisées: {', '.join(ALLOWED_ROLES)}")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
        return v

    @model_validator(mode="after")
    def normalize_email(self) -> "UserUpdateRequest":
        if self.email is not None:
            self.email = self.email.strip().lower()
        return self


class DeactivateResponse(BaseModel):
    id: str
    is_active: bool
    message: str
