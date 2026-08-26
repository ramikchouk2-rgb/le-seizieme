from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import require_manager_or_admin
from app.models.transport_assignment import (
    TransportConfirmationRequest,
    TransportConfirmationResponse,
    TransportRecommendationResponse,
    TransportUnassignedPassengerResponse,
)
from app.services.event_service import confirm_transport
from app.services.transport_engine import recommend_transport

router = APIRouter()


@router.post("/events/{event_id}/recommend-transport", response_model=TransportRecommendationResponse, dependencies=[Depends(require_manager_or_admin)])
async def recommend_transport_endpoint(event_id: str) -> TransportRecommendationResponse:
    result = await recommend_transport(event_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return TransportRecommendationResponse(
        event_id=result["event_id"],
        transport_status=result["transport_status"],
        drivers=[TransportDriverResponse(**d) for d in result.get("drivers", [])],
        passengers=[TransportPassengerResponse(**p) for p in result.get("passengers", [])],
        unassigned_passengers=[TransportUnassignedPassengerResponse(**u) for u in result.get("unassigned_passengers", [])],
        total_selected=result.get("total_selected", 0),
        total_assigned=result.get("total_assigned", 0),
        total_unassigned=result.get("total_unassigned", 0),
    )


@router.post("/events/{event_id}/confirm-transport", response_model=TransportConfirmationResponse, dependencies=[Depends(require_manager_or_admin)])
async def confirm_transport_endpoint(event_id: str, payload: TransportConfirmationRequest) -> TransportConfirmationResponse:
    groups = []
    for g in payload.groups:
        passengers = []
        for p in g.passengers:
            passengers.append({"server_id": str(p.server_id), "pickup_order": p.pickup_order})
        groups.append({"driver_server_id": str(g.driver_server_id), "passengers": passengers})
    result = await confirm_transport(event_id, groups)
    return TransportConfirmationResponse(**result)
