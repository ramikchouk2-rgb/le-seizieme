from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user_dep, require_manager_or_admin
from app.models.servers import (
    ServerAvailabilityCreateRequest,
    ServerAvailabilityListResponse,
    ServerAvailabilityResponse,
    ServerAvailabilityUpdateRequest,
    ServerCreateRequest,
    ServerListItem,
    ServerListResponse,
    ServerProfileResponse,
    ServerSkillCreateRequest,
    ServerSkillResponse,
    ServerSkillUpdateRequest,
    ServerStatsResponse,
    ServerUpdateRequest,
    ServerVehicleCreateRequest,
    ServerVehicleResponse,
    ServerVehicleUpdateRequest,
    ServerResponse,
)
from app.services.server_service import (
    add_server_skill,
    create_server,
    load_server_detail,
    load_server_list,
    load_server_stats,
    remove_server_skill,
    update_server,
    update_server_skill,
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


@router.post("/servers", response_model=ServerResponse, dependencies=[Depends(require_manager_or_admin)])
async def create_server_endpoint(payload: ServerCreateRequest) -> ServerResponse:
    result = await create_server(payload.model_dump())
    return ServerResponse(**result)


@router.patch("/servers/{server_id}", response_model=ServerResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_server_endpoint(server_id: str, payload: ServerUpdateRequest) -> ServerResponse:
    result = await update_server(server_id, payload.model_dump(exclude_unset=True))
    return ServerResponse(**result)


@router.post("/servers/{server_id}/skills", response_model=ServerSkillResponse, dependencies=[Depends(require_manager_or_admin)])
async def add_skill_endpoint(server_id: str, payload: ServerSkillCreateRequest) -> ServerSkillResponse:
    result = await add_server_skill(server_id, payload.model_dump())
    return ServerSkillResponse(**result)


@router.patch("/servers/{server_id}/skills/{skill_id}", response_model=ServerSkillResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_skill_endpoint(server_id: str, skill_id: str, payload: ServerSkillUpdateRequest) -> ServerSkillResponse:
    result = await update_server_skill(server_id, skill_id, payload.model_dump(exclude_unset=True))
    return ServerSkillResponse(**result)


@router.delete("/servers/{server_id}/skills/{skill_id}", dependencies=[Depends(require_manager_or_admin)])
async def remove_skill_endpoint(server_id: str, skill_id: str) -> dict[str, str]:
    await remove_server_skill(server_id, skill_id)
    return {"message": "Compétence supprimée avec succès."}
