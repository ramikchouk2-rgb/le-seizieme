from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user_dep
from app.models.servers import (
    ServerListResponse,
    ServerListItem,
    ServerProfileResponse,
    ServerStatsResponse,
)
from app.services.server_service import (
    load_server_detail,
    load_server_list,
    load_server_stats,
)

router = APIRouter()


@router.get("/servers", response_model=ServerListResponse, dependencies=[Depends(get_current_user_dep)])
async def get_servers(
    search: str | None = Query(default=None),
    city: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    availability: str | None = Query(default=None),
    worker_type: str | None = Query(default=None),
    has_vehicle: bool | None = Query(default=None),
    can_transport: bool | None = Query(default=None),
    location_verified: bool | None = Query(default=None),
    min_experience: int | None = Query(default=None, ge=0),
    max_experience: int | None = Query(default=None, ge=0),
    skill: str | None = Query(default=None),
    sort_by: str | None = Query(default="first_name"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> ServerListResponse:
    items, total = await load_server_list(
        search=search,
        city=city,
        gender=gender,
        availability=availability,
        worker_type=worker_type,
        has_vehicle=has_vehicle,
        can_transport=can_transport,
        location_verified=location_verified,
        min_experience=min_experience,
        max_experience=max_experience,
        skill=skill,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, -(-total // page_size))
    return ServerListResponse(
        items=[ServerListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/servers/stats", response_model=ServerStatsResponse, dependencies=[Depends(get_current_user_dep)])
async def get_servers_stats() -> ServerStatsResponse:
    stats = await load_server_stats()
    return ServerStatsResponse(**stats)


@router.get("/servers/{server_id}", response_model=ServerProfileResponse, dependencies=[Depends(get_current_user_dep)])
async def get_server_detail(server_id: str) -> ServerProfileResponse:
    data = await load_server_detail(server_id)
    if not data:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerProfileResponse(**data)
