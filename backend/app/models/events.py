from pydantic import BaseModel, field_validator
from typing import Optional, Any


class CityResponse(BaseModel):
    id: str
    name: str


def _validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> None:
    if latitude is not None and not (-90 <= latitude <= 90):
        raise ValueError('La latitude doit être comprise entre -90 et 90.')
    if longitude is not None and not (-180 <= longitude <= 180):
        raise ValueError('La longitude doit être comprise entre -180 et 180.')


class EventCoordinateMixin(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @field_validator('latitude')
    @classmethod
    def latitude_must_be_in_range(cls, v):
        _validate_coordinates(v, None)
        return v

    @field_validator('longitude')
    @classmethod
    def longitude_must_be_in_range(cls, v):
        _validate_coordinates(None, v)
        return v


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


class EventCreateRequest(EventCoordinateMixin):
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


class EventUpdateRequest(EventCoordinateMixin):
    name: Optional[str] = None
    client_name: Optional[str] = None
    city_id: Optional[str] = None
    address: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    guest_count: Optional[int] = None
    event_type: Optional[str] = None
    alcohol_service: Optional[bool] = None
    food_products_count: Optional[int] = None
    priority: Optional[str] = None
    is_urgent: Optional[bool] = None
    required_response_minutes: Optional[int] = None
    notes: Optional[str] = None

    @field_validator('guest_count')
    @classmethod
    def guest_count_must_be_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError('Le nombre d\'invités doit être au moins 1.')
        return v


class EventCreateResponse(EventCoordinateMixin):
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


class EventStaffResponse(BaseModel):
    id: str
    server_id: str
    server_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
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
    conflict: bool = False
    conflict_reason: Optional[str] = None


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


class EventDetailEventResponse(EventCoordinateMixin):
    # Step 24C-D-2: client_name, event_type, required_response_minutes and
    # notes were already selected and emitted by get_event_staff_summary(), but
    # because this model did not declare them the response_model filtered them
    # out and the detail payload silently lost four fields that the events table
    # has always held. They are declared here so the contract matches reality.
    id: str
    name: str
    client_name: str
    city: str
    city_id: Optional[str] = None
    address: Optional[str] = None
    start_datetime: str
    end_datetime: str
    guest_count: int
    event_type: str
    alcohol_service: bool
    food_products_count: int
    priority: str
    urgent: bool
    required_response_minutes: Optional[int] = None
    status: str
    notes: Optional[str] = None
    # Step 24C-D-4: False when the venue position shown/used came from the city
    # reference or the global technical fallback instead of the event's own
    # coordinates. Consumers must label any derived distance as approximate.
    has_exact_location: bool = True


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
    # Step 24C-D-4: end-to-end route distance (driver -> pickups -> venue),
    # distinct from the historical `estimated_distance_km` pickup sum.
    estimated_route_distance_km: Optional[float] = None
    # False when the venue leg was computed from the city reference or from the
    # global technical fallback rather than the event's own coordinates.
    has_exact_location: bool = True
    passengers: list[dict[str, Any]] = []
    status: str


class EventDetailTransportResponse(BaseModel):
    groups: list[EventDetailTransportGroupResponse]
    total_groups: int
    total_passengers: int


class EventDetailResponse(BaseModel):
    # Step 24C-D-3: this is the live event-detail envelope served by
    # GET /events/{event_id}. A flat EventDetailResponse previously also existed
    # earlier in this file; Python rebound the module name to this class, so the
    # earlier one was unreachable and any edit to it had no effect on the API.
    # It has been removed. Do not reintroduce a second EventDetailResponse.
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


# ---------------------------------------------------------------- print data
#
# Step 24C-D-8B. An explicit, dedicated contract for the future print sheet,
# kept separate from EventDetailResponse so the existing event-detail API is
# untouched.
#
# The central distinction this contract makes is REQUIRED MINIMUM vs ACTUAL
# SKILL. The existing event detail exposes `assignments[].skill_level`, which is
# the requirement's minimum and is rendered in the UI as a per-server figure.
# That field is left exactly as it is; here the two values get honest, separate
# names so no consumer can confuse them again.


class EventPrintEventResponse(BaseModel):
    """Venue and event facts for the print sheet header.

    `latitude`/`longitude` are the RESOLVED VENUE position (exact event
    coordinates, else the city reference, else the global fallback) and
    `has_exact_location` says which. Server GPS is never present at any level.
    """

    id: str
    name: str
    client_name: Optional[str] = None
    event_type: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    guest_count: Optional[int] = None
    status: str
    priority: Optional[str] = None
    urgent: bool = False
    # Only the relative budget is exposed. No absolute deadline timestamp is
    # computed here: the backend has no authoritative "response deadline"
    # calculation for an event, and inventing a second one would create a
    # competing source of truth.
    required_response_minutes: Optional[int] = None
    notes: Optional[str] = None
    has_exact_location: bool = True


class EventPrintRequirementResponse(BaseModel):
    """One staffing requirement, with the minimum level named for what it is.

    `event_requirements` has NO skill_id, so `required_minimum_skill_level` is a
    bare numeric threshold. No skill name is attached to it and none is
    inferred from `role_name`.
    """

    requirement_id: str
    role_name: str
    quantity: int
    required_gender: Optional[str] = None
    minimum_experience: int = 0
    required_minimum_skill_level: int
    selected: int = 0
    missing: int = 0


class EventPrintActualSkillResponse(BaseModel):
    """A real `server_skills` record: the server's actual capability.

    Distinct from EventPrintRequirementResponse.required_minimum_skill_level,
    which is a requirement, not a capability.
    """

    skill_id: str
    skill_name: str
    level: int
    years_experience: int


class EventPrintVerifiedAttestationResponse(BaseModel):
    """Qualification metadata only. Never bytes, a path or a URL.

    `status` is always "VERIFIED": the service filters on it, so any other value
    reaching a client would be a bug rather than a value to display.
    """

    attestation_id: str
    qualification_name: str
    status: str
    verified_at: Optional[str] = None


class EventPrintAssignmentResponse(BaseModel):
    """One assigned server, for the staffing section of the sheet.

    Deliberately absent: phone, email, the server's own coordinates, location
    history, file URLs and any audit detail. `profile_photo_available` is a
    boolean: the print page fetches the image through the existing
    authenticated endpoint, one server at a time.
    """

    server_id: str
    first_name: str
    last_name: str
    gender: Optional[str] = None
    city: Optional[str] = None
    years_experience: Optional[int] = None
    role: str
    assignment_status: str
    assigned_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    # Step 24C-D-8B-FIX. The service has always built this per assignment, to
    # make a printed row self-contained, but the field was never declared here,
    # so FastAPI silently dropped it from the HTTP response while the
    # service-level test still passed.
    #
    # Required, not optional: `event_requirements.minimum_skill_level` is
    # NOT NULL, and the service's own fallback for an unmatched role is 1. The
    # value is therefore always an int and null would mean a bug.
    #
    # A REQUIREMENT, not a capability -- compare `actual_skills` below.
    required_minimum_skill_level: int
    # Populated only from an already-persisted value. No score is recomputed
    # here: selection scoring is a staffing concern, not a print concern.
    score: Optional[float] = None
    # Step 24C-D-9: the uniform size this server wears, so a sheet can show what
    # is available. Nullable: null means never recorded, and the print page must
    # label it rather than assume a default.
    uniform_size: Optional[str] = None
    profile_photo_available: bool = False
    actual_skills: list[EventPrintActualSkillResponse] = []
    verified_attestations: list[EventPrintVerifiedAttestationResponse] = []


class EventPrintPassengerResponse(BaseModel):
    server_id: str
    name: str
    pickup_order: int
    pickup_status: str
    pickup_location_label: str


class EventPrintTransportGroupResponse(BaseModel):
    """One confirmed transport group, for the logistics section.

    Internal route coordinates are used to compute
    `estimated_route_distance_km` and are never returned. Only human-readable
    labels travel to the client.
    """

    transport_group_id: str
    driver_server_id: str
    driver_name: str
    vehicle: str
    vehicle_type: Optional[str] = None
    capacity: int
    passenger_count: int
    departure_time: Optional[str] = None
    departure_location_label: str
    destination_label: str
    estimated_duration_minutes: Optional[int] = None
    estimated_distance_km: Optional[float] = None
    estimated_route_distance_km: Optional[float] = None
    has_exact_location: bool = True
    status: str
    passengers: list[EventPrintPassengerResponse] = []


class EventPrintDataResponse(BaseModel):
    """The full print-data contract for GET /events/{event_id}/print-data."""

    event: EventPrintEventResponse
    requirements: list[EventPrintRequirementResponse] = []
    assignments: list[EventPrintAssignmentResponse] = []
    transport_groups: list[EventPrintTransportGroupResponse] = []
