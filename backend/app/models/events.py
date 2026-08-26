from pydantic import BaseModel, field_validator
from typing import Optional, Any


class CityResponse(BaseModel):
    id: str
    name: str


class EventRequirementDetailResponse(BaseModel):
    requirement_id: str
    role_name: str
    quantity: int
    required_gender: Optional[str]
    minimum_experience: int
    minimum_skill_level: int
    selected: int
    missing: int


class RequirementCreateRequest(BaseModel):
    role_name: str
    quantity: int
    minimum_skill_level: int = 1
    minimum_experience: int = 0
    required_gender: Optional[str] = None

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v < 1:
            raise ValueError('La quantité doit être au moins 1.')
        return v

    @field_validator('minimum_skill_level')
    @classmethod
    def skill_must_be_valid(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Le niveau de compétence doit être entre 1 et 10.')
        return v

    @field_validator('minimum_experience')
    @classmethod
    def experience_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('L\'expérience ne peut pas être négative.')
        return v

    @field_validator('required_gender')
    @classmethod
    def gender_must_be_valid(cls, v):
        if v is not None and v not in ('MALE', 'FEMALE', 'OTHER'):
            raise ValueError('Genre invalide.')
        return v


class RequirementUpdateRequest(BaseModel):
    role_name: Optional[str] = None
    quantity: Optional[int] = None
    minimum_skill_level: Optional[int] = None
    minimum_experience: Optional[int] = None
    required_gender: Optional[str] = None

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError('La quantité doit être au moins 1.')
        return v

    @field_validator('minimum_skill_level')
    @classmethod
    def skill_must_be_valid(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError('Le niveau de compétence doit être entre 1 et 10.')
        return v

    @field_validator('minimum_experience')
    @classmethod
    def experience_must_be_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('L\'expérience ne peut pas être négative.')
        return v

    @field_validator('required_gender')
    @classmethod
    def gender_must_be_valid(cls, v):
        if v is not None and v not in ('MALE', 'FEMALE', 'OTHER'):
            raise ValueError('Genre invalide.')
        return v


class RequirementResponse(BaseModel):
    requirement_id: str
    role_name: str
    quantity: int
    required_gender: Optional[str]
    minimum_experience: int
    minimum_skill_level: int
    selected: int
    missing: int


class EventCreateRequest(BaseModel):
    name: str
    client_name: str
    city_id: str
    address: str
    start_datetime: str
    end_datetime: str
    guest_count: int
    event_type: str
    alcohol_service: bool = False
    food_products_count: int = 0
    priority: str = "NORMAL"
    is_urgent: bool = False
    required_response_minutes: Optional[int] = None
    status: str = "PLANNED"
    notes: Optional[str] = None


class EventCreateResponse(BaseModel):
    id: str
    name: str
    client_name: str
    city_id: str
    address: str
    start_datetime: str
    end_datetime: str
    guest_count: int
    event_type: str
    alcohol_service: bool
    food_products_count: int
    priority: str
    is_urgent: bool
    required_response_minutes: Optional[int]
    status: str
    notes: Optional[str]
    created_at: str
    updated_at: str


class EventDetailResponse(BaseModel):
    id: str
    name: str
    city: str
    start_datetime: str
    end_datetime: str
    guest_count: int
    alcohol_service: bool
    food_products_count: int
    priority: str
    urgent: bool
    status: str
    requirements: list[EventRequirementDetailResponse]


class EventStaffResponse(BaseModel):
    id: str
    server_id: str
    server_name: str
    gender: str
    city: str
    role: str
    required_gender: Optional[str]
    score: Optional[float]
    distance_km: Optional[float]
    years_experience: int
    skill_level: int
    availability_status: str
    status: str
    reasons: list[str]


class EventStaffListResponse(BaseModel):
    event_id: str
    event_name: str
    city: str
    status: str
    staffing: dict
    requirements: list[EventRequirementDetailResponse]
    assignments: list[EventStaffResponse]


class EventListItem(BaseModel):
    id: str
    name: str
    city: str
    start_datetime: str
    end_datetime: str
    guest_count: int
    alcohol_service: bool
    food_products_count: int
    priority: str
    urgent: bool
    status: str
    staffing: dict[str, Any]


class EventListResponse(BaseModel):
    items: list[EventListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class EventStatsResponse(BaseModel):
    upcoming_events: int
    planned_events: int
    urgent_events: int
    missing_positions: int


class EventStatusUpdateRequest(BaseModel):
    status: str

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = ('PLANNED', 'STAFFING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')
        if v not in allowed:
            raise ValueError(f'Statut invalide. Valeurs autorisées: {", ".join(allowed)}')
        return v


class EventStatusUpdateResponse(BaseModel):
    event_id: str
    status: str
    previous_status: str
    message: str


class EventOperationsRequirement(BaseModel):
    requirement_id: str
    role_name: str
    quantity: int
    required_gender: Optional[str]
    minimum_experience: int
    minimum_skill_level: int
    assigned: int
    confirmed: int
    missing: int
    status: str


class EventOperationsStaff(BaseModel):
    assignment_id: str
    server_id: str
    server_name: str
    role: str
    assignment_status: str
    years_experience: Optional[int] = None
    skill_level: Optional[int] = None
    score: Optional[float] = None
    transport_status: Optional[str] = None


class EventOperationsTransportGroup(BaseModel):
    group_id: str
    driver_name: str
    vehicle: str
    capacity: int
    passenger_count: int
    available_seats: int
    status: str
    passengers: list[dict[str, Any]] = []


class EventOperationsTransport(BaseModel):
    groups: list[EventOperationsTransportGroup]
    total_groups: int
    total_passengers: int
    unassigned_passengers: int = 0


class OperationalAlert(BaseModel):
    type: str
    severity: str
    message: str
    related_entity: Optional[str] = None


class EventOperationsResponse(BaseModel):
    event_id: str
    event_name: str
    status: str
    city: str
    date: str
    guest_count: int
    duration_minutes: Optional[int] = None
    attendance_available: bool = False
    attendance: Optional[dict[str, Any]] = None
    staffing_summary: dict[str, Any]
    requirements: list[EventOperationsRequirement]
    confirmed_staff: list[EventOperationsStaff]
    transport: EventOperationsTransport
    alerts: list[OperationalAlert]


class EventDetailEventResponse(BaseModel):
    id: str
    name: str
    city: str
    start_datetime: str
    end_datetime: str
    guest_count: int
    alcohol_service: bool
    food_products_count: int
    priority: str
    urgent: bool
    status: str


class EventDetailStaffingResponse(BaseModel):
    requested: int
    selected: int
    missing: int
    percentage: int


class EventDetailTransportGroupResponse(BaseModel):
    group_id: str
    driver_server_id: str
    driver_name: str
    vehicle: str
    capacity: int
    passenger_count: int
    estimated_distance_km: Optional[float] = None
    passengers: list[dict[str, Any]] = []
    status: str


class EventDetailTransportResponse(BaseModel):
    groups: list[EventDetailTransportGroupResponse]
    total_groups: int
    total_passengers: int


class EventDetailResponse(BaseModel):
    event: EventDetailEventResponse
    staffing: EventDetailStaffingResponse
    requirements: list[EventRequirementDetailResponse]
    assignments: list[dict[str, Any]]
    transport: EventDetailTransportResponse


class EventRequirementsResponse(BaseModel):
    event_id: str
    requirements: list[EventRequirementDetailResponse]


class DeleteResponse(BaseModel):
    deleted: bool = True
