from pydantic import BaseModel
from typing import Optional, Any


class EventReportRequirement(BaseModel):
    requirement_id: str
    role: str
    requested: int
    assigned: int
    confirmed: int
    fulfilled: bool
    status: str


class EventReportStaff(BaseModel):
    server_id: str
    name: str
    role: str
    assignment_status: str
    attendance_status: Optional[str] = None
    check_in_at: Optional[str] = None
    check_out_at: Optional[str] = None
    completion_points: int = 0
    performance_points: int = 0
    total_points: int = 0
    evaluation_score: Optional[float] = None
    evaluation_comment: Optional[str] = None
    evaluated: bool = False


class EventReportTransport(BaseModel):
    total_groups: int
    confirmed_groups: int
    total_passengers: int
    assigned_passengers: int
    unassigned_passengers: int


class EventReportGamification(BaseModel):
    completion_points: int
    performance_points: int
    total_points: int


class EventReportKpi(BaseModel):
    staffing_rate: float
    attendance_rate: float
    requirement_fulfillment_rate: float
    transport_coverage_rate: float


class EventReportAlert(BaseModel):
    type: str
    severity: str
    message: str
    related_entity: Optional[str] = None


class EventReportEvaluationSummary(BaseModel):
    total_evaluated: int
    total_confirmed: int
    evaluation_coverage: float
    average_score: Optional[float]
    highest_score: Optional[float]
    lowest_score: Optional[float]
    excellent_count: int = 0
    good_count: int = 0
    average_count: int = 0
    needs_improvement_count: int = 0


class EventReportResponse(BaseModel):
    event_id: str
    event_name: str
    status: str
    is_final: bool
    event: dict[str, Any]
    staffing: dict[str, Any]
    requirements: list[EventReportRequirement]
    attendance: dict[str, Any]
    staff: list[EventReportStaff]
    transport: EventReportTransport
    gamification: EventReportGamification
    final_kpis: EventReportKpi
    evaluation_summary: Optional[EventReportEvaluationSummary] = None
    alerts: list[EventReportAlert]
    generated_at: str
