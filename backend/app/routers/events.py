from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.deps import get_current_user_dep, require_manager_or_admin
from app.core.database import get_pool
from app.models.assignment import (
    AddStaffAssignmentRequest,
    ConfirmStaffAssignmentRequest,
    ConfirmStaffResponse,
    EligibleStaffResponse,
    StaffAssignmentResponse,
    UpdateStaffAssignmentRequest,
)
from app.models.events import (
    CityResponse,
    EventCreateRequest,
    EventCreateResponse,
    EventDetailEventResponse,
    EventDetailResponse,
    EventDetailStaffingResponse,
    EventDetailTransportGroupResponse,
    EventDetailTransportResponse,
    EventListItem,
    EventListResponse,
    EventOperationsResponse,
    EventRequirementDetailResponse,
    EventRequirementsResponse,
    EventStaffListResponse,
    EventStatsResponse,
    EventStatusUpdateRequest,
    EventStatusUpdateResponse,
    EventUpdateRequest,
    RequirementCreateRequest,
    RequirementResponse,
    RequirementUpdateRequest,
    DeleteResponse,
)
from app.models.event_report import EventReportResponse
from app.models.evaluations import (
    EvaluationCreateRequest,
    EvaluationUpdateRequest,
    EvaluationResponse,
)
from app.models.attendance import (
    AttendanceActionResponse,
    AttendanceInitializeResponse,
    AttendanceListResponse,
    AttendanceResponse,
    AttendanceSummaryResponse,
    CheckInRequest,
    CheckOutRequest,
    AttendanceStatusUpdateRequest,
)
from app.models.selection import StaffRecommendationResponse
from app.services.event_service import (
    add_staff_assignment,
    confirm_staff_assignments,
    create_event,
    create_requirement,
    delete_requirement,
    get_eligible_staff,
    get_event_operations,
    get_event_staff_summary,
    load_cities,
    load_event_list,
    load_event_stats,
    remove_staff_assignment,
    update_event,
    update_event_status,
    update_requirement,
    update_staff_assignment,
)
from app.services.attendance_service import (
    check_in_staff,
    check_out_staff,
    get_attendance_summary,
    get_event_attendance,
    initialize_event_attendance,
    update_attendance_status,
)
from app.services.event_report_service import get_event_report
from app.services.evaluation_service import (
    create_evaluation,
    delete_evaluation,
    get_event_evaluations,
    get_evaluation,
    update_evaluation,
)
from app.services.selection_engine import generate_staff_recommendations

router = APIRouter()


@router.get("/cities", response_model=list[CityResponse], dependencies=[Depends(get_current_user_dep)])
async def get_cities() -> list[CityResponse]:
    rows = await load_cities()
    return [CityResponse(id=str(r["id"]), name=r["name"]) for r in rows]


@router.post("/events", response_model=EventCreateResponse, dependencies=[Depends(require_manager_or_admin)])
async def create_event_endpoint(payload: EventCreateRequest) -> EventCreateResponse:
    result = await create_event(payload.model_dump())
    return EventCreateResponse(
        id=str(result["id"]),
        name=result["name"],
        client_name=result["client_name"],
        city_id=str(result["city_id"]),
        address=result["address"],
        start_datetime=result["start_datetime"].isoformat() if result.get("start_datetime") else "",
        end_datetime=result["end_datetime"].isoformat() if result.get("end_datetime") else "",
        guest_count=result["guest_count"],
        event_type=result["event_type"],
        alcohol_service=result["alcohol_service"],
        food_products_count=result["food_products_count"],
        priority=result["priority"],
        is_urgent=result["is_urgent"],
        required_response_minutes=result.get("required_response_minutes"),
        status=result["status"],
        notes=result.get("notes"),
        created_at=result["created_at"].isoformat() if result.get("created_at") else "",
        updated_at=result["updated_at"].isoformat() if result.get("updated_at") else "",
    )


@router.patch("/events/{event_id}", response_model=EventCreateResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_event_endpoint(event_id: str, payload: EventUpdateRequest) -> EventCreateResponse:
    result = await update_event(event_id, payload.model_dump(exclude_unset=True))
    return EventCreateResponse(
        id=str(result["id"]),
        name=result["name"],
        client_name=result["client_name"],
        city_id=str(result["city_id"]),
        address=result["address"],
        start_datetime=result["start_datetime"].isoformat() if result.get("start_datetime") else "",
        end_datetime=result["end_datetime"].isoformat() if result.get("end_datetime") else "",
        guest_count=result["guest_count"],
        event_type=result["event_type"],
        alcohol_service=result["alcohol_service"],
        food_products_count=result["food_products_count"],
        priority=result["priority"],
        is_urgent=result["is_urgent"],
        required_response_minutes=result.get("required_response_minutes"),
        status=result["status"],
        notes=result.get("notes"),
        created_at=result["created_at"].isoformat() if result.get("created_at") else "",
        updated_at=result["updated_at"].isoformat() if result.get("updated_at") else "",
    )


@router.get("/events", response_model=EventListResponse, dependencies=[Depends(get_current_user_dep)])
async def get_events(
    search: str | None = Query(default=None),
    city: str | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    urgent: bool | None = Query(default=None),
    staffing: str | None = Query(default=None),
    date_range: str | None = Query(default=None),
    sort_by: str | None = Query(default="date"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> EventListResponse:
    items, total = await load_event_list(
        search=search,
        city=city,
        status=status,
        priority=priority,
        urgent=urgent,
        staffing=staffing,
        date_range=date_range,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, -(-total // page_size))
    return EventListResponse(
        items=[EventListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/events/stats", response_model=EventStatsResponse, dependencies=[Depends(get_current_user_dep)])
async def get_events_stats() -> EventStatsResponse:
    stats = await load_event_stats()
    return EventStatsResponse(**stats)


@router.post("/events/{event_id}/generate-staff", response_model=StaffRecommendationResponse, dependencies=[Depends(require_manager_or_admin)])
async def generate_staff(event_id: str) -> StaffRecommendationResponse:
    result = await generate_staff_recommendations(event_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return StaffRecommendationResponse(**result)


@router.post("/events/{event_id}/confirm-staff", response_model=ConfirmStaffResponse, dependencies=[Depends(require_manager_or_admin)])
async def confirm_staff(event_id: str, payload: ConfirmStaffAssignmentRequest) -> ConfirmStaffResponse:
    result = await confirm_staff_assignments(event_id, [dict(a) for a in payload.assignments])
    return ConfirmStaffResponse(**result)


@router.get("/events/{event_id}/operations", response_model=EventOperationsResponse, dependencies=[Depends(get_current_user_dep)])
async def get_event_operations_endpoint(event_id: str):
    data = await get_event_operations(event_id)
    return EventOperationsResponse(**data)


@router.get("/events/{event_id}/attendance", response_model=AttendanceListResponse, dependencies=[Depends(get_current_user_dep)])
async def get_attendance(event_id: str):
    data = await get_event_attendance(event_id)
    return AttendanceListResponse(
        event_id=data["event_id"],
        summary=data["summary"],
        staff=[AttendanceResponse(**s) for s in data["staff"]],
    )


@router.post("/events/{event_id}/attendance/initialize", response_model=AttendanceInitializeResponse, dependencies=[Depends(require_manager_or_admin)])
async def initialize_attendance(event_id: str):
    data = await initialize_event_attendance(event_id)
    return AttendanceInitializeResponse(**data)


@router.post("/events/{event_id}/attendance/{event_staff_id}/check-in", response_model=AttendanceActionResponse, dependencies=[Depends(require_manager_or_admin)])
async def check_in(event_id: str, event_staff_id: str, payload: CheckInRequest) -> AttendanceActionResponse:
    data = await check_in_staff(event_id, event_staff_id, payload.note)
    return AttendanceActionResponse(**data)


@router.post("/events/{event_id}/attendance/{event_staff_id}/check-out", response_model=AttendanceActionResponse, dependencies=[Depends(require_manager_or_admin)])
async def check_out(event_id: str, event_staff_id: str, payload: CheckOutRequest) -> AttendanceActionResponse:
    data = await check_out_staff(event_id, event_staff_id, payload.note)
    return AttendanceActionResponse(**data)


@router.patch("/events/{event_id}/attendance/{event_staff_id}", response_model=AttendanceActionResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_status(event_id: str, event_staff_id: str, payload: AttendanceStatusUpdateRequest) -> AttendanceActionResponse:
    data = await update_attendance_status(event_id, event_staff_id, payload.status, payload.note)
    return AttendanceActionResponse(**data)


@router.get("/events/{event_id}/attendance/summary", response_model=AttendanceSummaryResponse, dependencies=[Depends(get_current_user_dep)])
async def get_attendance_summary_endpoint(event_id: str):
    data = await get_attendance_summary(event_id)
    return AttendanceSummaryResponse(**data)


@router.get("/events/{event_id}/report", response_model=EventReportResponse, dependencies=[Depends(get_current_user_dep)])
async def get_event_report_endpoint(event_id: str):
    data = await get_event_report(event_id)
    return EventReportResponse(**data)


@router.get("/events/{event_id}/evaluations", response_model=list[EvaluationResponse], dependencies=[Depends(get_current_user_dep)])
async def get_event_evaluations_endpoint(event_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            "SELECT id FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")
    data = await get_event_evaluations(event_id)
    return [EvaluationResponse(**e) for e in data]


@router.get("/events/{event_id}/evaluations/{evaluation_id}", response_model=EvaluationResponse, dependencies=[Depends(get_current_user_dep)])
async def get_evaluation_endpoint(event_id: str, evaluation_id: str):
    data = await get_evaluation(event_id, evaluation_id)
    if not data:
        raise HTTPException(status_code=404, detail="Évaluation introuvable.")
    return EvaluationResponse(**data)


@router.post("/events/{event_id}/evaluations", response_model=EvaluationResponse, status_code=201, dependencies=[Depends(require_manager_or_admin)])
async def create_evaluation_endpoint(event_id: str, payload: EvaluationCreateRequest):
    data = await create_evaluation(event_id, payload.model_dump())
    return EvaluationResponse(**data)


@router.patch("/events/{event_id}/evaluations/{evaluation_id}", response_model=EvaluationResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_evaluation_endpoint(event_id: str, evaluation_id: str, payload: EvaluationUpdateRequest):
    data = await update_evaluation(event_id, evaluation_id, payload.model_dump(exclude_unset=True))
    return EvaluationResponse(**data)


@router.delete("/events/{event_id}/evaluations/{evaluation_id}", response_model=DeleteResponse, dependencies=[Depends(require_manager_or_admin)])
async def delete_evaluation_endpoint(event_id: str, evaluation_id: str) -> DeleteResponse:
    result = await delete_evaluation(event_id, evaluation_id)
    return DeleteResponse(**result)


@router.get("/events/{event_id}", response_model=EventDetailResponse, dependencies=[Depends(get_current_user_dep)])
async def get_event_detail(event_id: str) -> EventDetailResponse:
    data = await get_event_staff_summary(event_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/events/{event_id}/requirements", response_model=EventRequirementsResponse, dependencies=[Depends(get_current_user_dep)])
async def get_requirements(event_id: str) -> EventRequirementsResponse:
    data = await get_event_staff_summary(event_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return EventRequirementsResponse(
        event_id=event_id,
        requirements=[EventRequirementDetailResponse(**r) for r in data.get("requirements", [])],
    )


@router.post("/events/{event_id}/requirements", response_model=RequirementResponse, dependencies=[Depends(require_manager_or_admin)])
async def create_requirement_endpoint(event_id: str, payload: RequirementCreateRequest):
    result = await create_requirement(event_id, payload.model_dump())
    return result


@router.patch("/events/{event_id}/requirements/{requirement_id}", response_model=RequirementResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_requirement_endpoint(event_id: str, requirement_id: str, payload: RequirementUpdateRequest):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Aucune modification fournie.")
    result = await update_requirement(event_id, requirement_id, data)
    return result


@router.delete("/events/{event_id}/requirements/{requirement_id}", response_model=DeleteResponse, dependencies=[Depends(require_manager_or_admin)])
async def delete_requirement_endpoint(event_id: str, requirement_id: str) -> DeleteResponse:
    result = await delete_requirement(event_id, requirement_id)
    return DeleteResponse(**result)


@router.post("/events/{event_id}/staff", response_model=StaffAssignmentResponse, dependencies=[Depends(require_manager_or_admin)])
async def add_staff(event_id: str, payload: AddStaffAssignmentRequest):
    result = await add_staff_assignment(event_id, payload.model_dump())
    return result


@router.delete("/events/{event_id}/staff/{assignment_id}", response_model=DeleteResponse, dependencies=[Depends(require_manager_or_admin)])
async def remove_staff(event_id: str, assignment_id: str) -> DeleteResponse:
    result = await remove_staff_assignment(event_id, assignment_id)
    return DeleteResponse(**result)


@router.patch("/events/{event_id}/staff/{assignment_id}", response_model=StaffAssignmentResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_staff(event_id: str, assignment_id: str, payload: UpdateStaffAssignmentRequest):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Aucune modification fournie.")
    result = await update_staff_assignment(event_id, assignment_id, data)
    return result


@router.get("/events/{event_id}/eligible-staff", response_model=list[EligibleStaffResponse], dependencies=[Depends(get_current_user_dep)])
async def get_eligible_staff_endpoint(
    event_id: str,
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
):
    data = await get_eligible_staff(event_id, search=search, role=role)
    return data


@router.patch("/events/{event_id}/status", response_model=EventStatusUpdateResponse, dependencies=[Depends(require_manager_or_admin)])
async def update_event_status_endpoint(event_id: str, payload: EventStatusUpdateRequest):
    data = await update_event_status(event_id, payload.status)
    return EventStatusUpdateResponse(**data)
