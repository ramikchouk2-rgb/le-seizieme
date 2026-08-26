from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user_dep, require_manager_or_admin
from app.models.urgent import UrgentActionResponse, UrgentGenerateResponse, UrgentStatusResponse
from app.services.urgent_engine import (
    accept_offer,
    decline_offer,
    expire_offer,
    generate_urgent_offers,
    get_urgent_status,
)

router = APIRouter()


@router.post("/events/{event_id}/urgent-offers/generate", response_model=UrgentGenerateResponse, dependencies=[Depends(require_manager_or_admin)])
async def generate_offers(event_id: str) -> UrgentGenerateResponse:
    result = await generate_urgent_offers(event_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    return UrgentGenerateResponse(**result)


@router.post("/events/{event_id}/urgent-offers/{offer_id}/accept", response_model=UrgentActionResponse, dependencies=[Depends(require_manager_or_admin)])
async def accept_offer_endpoint(event_id: str, offer_id: str) -> UrgentActionResponse:
    result = await accept_offer(event_id, offer_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    urgent_status = await get_urgent_status(event_id)
    return UrgentActionResponse(
        success=True,
        message="Offre acceptée avec succès.",
        offer=result.get("event_staff"),
        urgent_status=urgent_status,
    )


@router.post("/events/{event_id}/urgent-offers/{offer_id}/decline", response_model=UrgentActionResponse, dependencies=[Depends(require_manager_or_admin)])
async def decline_offer_endpoint(event_id: str, offer_id: str) -> UrgentActionResponse:
    result = await decline_offer(event_id, offer_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    urgent_status = await get_urgent_status(event_id)
    return UrgentActionResponse(
        success=True,
        message="Offre refusée.",
        offer={"offer_id": result.get("offer_id")},
        urgent_status=urgent_status,
    )


@router.post("/events/{event_id}/urgent-offers/{offer_id}/expire", response_model=UrgentActionResponse, dependencies=[Depends(require_manager_or_admin)])
async def expire_offer_endpoint(event_id: str, offer_id: str) -> UrgentActionResponse:
    result = await expire_offer(event_id, offer_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    urgent_status = await get_urgent_status(event_id)
    return UrgentActionResponse(
        success=True,
        message="Offre expirée.",
        offer={"offer_id": result.get("offer_id")},
        urgent_status=urgent_status,
    )


@router.get("/events/{event_id}/urgent-status", response_model=UrgentStatusResponse, dependencies=[Depends(get_current_user_dep)])
async def urgent_status(event_id: str) -> UrgentStatusResponse:
    result = await get_urgent_status(event_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=404, detail=result.get("error", "Event not found"))
    return UrgentStatusResponse(**result)
