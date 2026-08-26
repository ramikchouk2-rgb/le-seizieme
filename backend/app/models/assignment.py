from pydantic import BaseModel, field_validator
from typing import Optional, Any


class ConfirmStaffAssignmentRequest(BaseModel):
    assignments: list[dict[str, str]]


class ConfirmStaffAssignmentResponse(BaseModel):
    server_id: str
    server_name: str
    role: str


class ConfirmStaffResponse(BaseModel):
    event_id: str
    status: str
    created_count: int
    assignments: list[ConfirmStaffAssignmentResponse]
    missing_positions: int


class AddStaffAssignmentRequest(BaseModel):
    server_id: str
    requirement_id: str
    role: str

    @field_validator('server_id')
    @classmethod
    def validate_server_id(cls, v):
        if not v:
            raise ValueError('server_id est requis.')
        return v

    @field_validator('requirement_id')
    @classmethod
    def validate_requirement_id(cls, v):
        if not v:
            raise ValueError('requirement_id est requis.')
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if not v or not v.strip():
            raise ValueError('Le rôle est requis.')
        return v.strip()


class UpdateStaffAssignmentRequest(BaseModel):
    role: Optional[str] = None
    assignment_status: Optional[str] = None
    requirement_id: Optional[str] = None

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Le rôle ne peut pas être vide.')
        return v.strip() if v else v

    @field_validator('assignment_status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ('PROPOSED', 'CONFIRMED', 'DECLINED', 'CANCELLED', 'COMPLETED'):
            raise ValueError('Statut d\'affectation invalide.')
        return v


class StaffAssignmentResponse(BaseModel):
    id: str
    event_id: str
    server_id: str
    server_name: str
    role: str
    status: str
    assigned_at: str
    confirmed_at: Optional[str] = None
    score: Optional[float] = None
    distance_km: Optional[float] = None
    years_experience: Optional[int] = None
    skill_level: Optional[int] = None
    availability_status: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    requirement_id: Optional[str] = None


class EligibleStaffResponse(BaseModel):
    server_id: str
    server_name: str
    gender: str
    city: str
    years_experience: int
    skill_level: int
    availability_status: str
    score: Optional[float] = None
    distance_km: Optional[float] = None
    requirement_id: Optional[str] = None
    role: Optional[str] = None
