from pydantic import BaseModel, field_validator
from typing import Optional


class AttendanceInitializeResponse(BaseModel):
    event_id: str
    initialized_count: int
    total_expected: int


class AttendanceResponse(BaseModel):
    id: str
    event_id: str
    event_staff_id: str
    server_id: str
    server_name: str
    role: str
    status: str
    check_in_at: Optional[str] = None
    check_out_at: Optional[str] = None
    note: Optional[str] = None


class AttendanceListResponse(BaseModel):
    event_id: str
    summary: dict[str, int]
    staff: list[AttendanceResponse]


class AttendanceSummaryResponse(BaseModel):
    event_id: str
    total_expected: int
    present: int
    late: int
    absent: int
    excused: int
    checked_out: int
    not_checked_in: int
    attendance_rate: float


class CheckInRequest(BaseModel):
    note: Optional[str] = None


class CheckOutRequest(BaseModel):
    note: Optional[str] = None


class AttendanceStatusUpdateRequest(BaseModel):
    status: str
    note: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = ('EXPECTED', 'PRESENT', 'LATE', 'ABSENT', 'EXCUSED', 'LEFT')
        if v not in allowed:
            raise ValueError(f'Statut invalide. Valeurs autorisées: {", ".join(allowed)}')
        return v


class AttendanceActionResponse(BaseModel):
    success: bool
    attendance_id: str
    message: str
    status: Optional[str] = None
