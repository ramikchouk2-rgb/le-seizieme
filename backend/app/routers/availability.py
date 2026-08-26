from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user_dep, require_manager_or_admin
from app.models.availability import (
    AvailabilityCheckResponse,
    AvailabilityCreateRequest,
    AvailabilityResponse,
    AvailabilityUpdateRequest,
    ServerAvailabilityListResponse,
)
from app.models.events import DeleteResponse
from app.services.availability_service import (
    check_availability_for_event,
    create_availability,
    delete_availability,
    get_server_availability,
    update_availability,
)

router = APIRouter()


@router.get("/servers/{server_id}/availability", response_model=ServerAvailabilityListResponse, dependencies=[Depends(get_current_user_dep)])
async def list_availability(server_id: str):
    items = await get_server_availability(server_id)
    return ServerAvailabilityListResponse(server_id=server_id, items=items)


@router.post("/servers/{server_id}/availability", response_model=AvailabilityResponse, status_code=201, dependencies=[Depends(require_manager_or_admin)])
async def create_availability_endpoint(server_id: str, payload: AvailabilityCreateRequest):
    data = await create_availability(server_id, payload.model_dump())
    return AvailabilityResponse(**data)


@router.patch("/servers/{server_id}/availability/{availability_id}", response_model=AvailabilityResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_availability_endpoint(server_id: str, availability_id: str, payload: AvailabilityUpdateRequest):
    data = await update_availability(server_id, availability_id, payload.model_dump(exclude_unset=True))
    return AvailabilityResponse(**data)


@router.delete("/servers/{server_id}/availability/{availability_id}", response_model=DeleteResponse, dependencies=[Depends(require_manager_or_admin)])
async def delete_availability_endpoint(server_id: str, availability_id: str) -> DeleteResponse:
    result = await delete_availability(server_id, availability_id)
    return DeleteResponse(**result)


@router.get("/servers/{server_id}/availability/check", response_model=AvailabilityCheckResponse, dependencies=[Depends(get_current_user_dep)])
async def check_availability(server_id: str, event_id: str = Query(...)):
    data = await check_availability_for_event(server_id, event_id)
    return AvailabilityCheckResponse(**data)
