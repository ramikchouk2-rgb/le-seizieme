from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import require_roles
from app.models.users import (
    DeactivateResponse,
    UserCreateRequest,
    UserDetail,
    UserListItem,
    UserListResponse,
    UserUpdateRequest,
)
from app.services.user_service import (
    create_user,
    deactivate_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter()


@router.get("/users", response_model=UserListResponse, dependencies=[Depends(require_roles("ADMIN"))])
async def list_users_endpoint(
    search: Optional[str] = Query(default=None),
    role: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> UserListResponse:
    items, total = await list_users(
        search=search,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, -(-total // page_size))
    return UserListResponse(
        items=[UserListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=UserDetail, dependencies=[Depends(require_roles("ADMIN"))])
async def get_user_endpoint(user_id: str) -> UserDetail:
    data = await get_user(user_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    return UserDetail(**data)


@router.post("/users", response_model=UserDetail, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("ADMIN"))])
async def create_user_endpoint(payload: UserCreateRequest) -> UserDetail:
    data = await create_user(payload.model_dump())
    return UserDetail(**data)


@router.patch("/users/{user_id}", response_model=UserDetail, dependencies=[Depends(require_roles("ADMIN"))])
async def update_user_endpoint(user_id: str, payload: UserUpdateRequest) -> UserDetail:
    data = await update_user(user_id, payload.model_dump(exclude_unset=True))
    return UserDetail(**data)


@router.patch("/users/{user_id}/deactivate", response_model=DeactivateResponse, dependencies=[Depends(require_roles("ADMIN"))])
async def deactivate_user_endpoint(user_id: str, current_user: dict = Depends(require_roles("ADMIN"))) -> DeactivateResponse:
    data = await deactivate_user(user_id, current_user["id"])
    return DeactivateResponse(**data)
