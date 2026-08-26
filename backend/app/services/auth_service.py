from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.core.database import get_pool
from app.core.security import decode_access_token, hash_password, verify_password
from app.models.auth import UserResponse


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, hashed_password, role, is_active FROM users WHERE email = $1",
            email,
        )
        if not row:
            return None
        return dict(row)


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, hashed_password, role, is_active FROM users WHERE id = $1",
            user_id,
        )
        if not row:
            return None
        return dict(row)


async def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = await get_user_by_email(email)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token_for_user(user: dict[str, Any]) -> str:
    from app.core.security import create_access_token
    from app.core.config import settings

    expire = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": str(user["id"]), "role": user["role"]},
        expires_delta=expire,
    )


async def get_current_user(token: str) -> dict[str, Any]:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré.")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token invalide.")

    user = await get_user_by_id(user_id)
    if user is None or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Utilisateur introuvable ou inactif.")

    return user


def require_roles(*allowed_roles: str):
    async def role_checker(current_user: dict[str, Any]) -> dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Permissions insuffisantes.",
            )
        return current_user

    return role_checker
