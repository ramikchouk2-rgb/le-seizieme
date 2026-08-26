from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.services.auth_service import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user_dep(token: str = Depends(oauth2_scheme)) -> dict:
    return await get_current_user(token)


def require_roles(*allowed_roles: str):
    async def role_checker(current_user: dict = Depends(get_current_user_dep)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes.",
            )
        return current_user

    return role_checker


def require_admin(current_user: dict = Depends(get_current_user_dep)) -> dict:
    if current_user["role"] != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissions insuffisantes.",
        )
    return current_user


def require_manager_or_admin(current_user: dict = Depends(get_current_user_dep)) -> dict:
    if current_user["role"] not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissions insuffisantes.",
        )
    return current_user
