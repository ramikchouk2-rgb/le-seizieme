from pydantic import BaseModel


class EventRequirementResponse(BaseModel):
    requirement_id: str
    role_name: str
    quantity: int
    required_gender: str | None
    minimum_experience: int
    minimum_skill_level: int


class EventResponse(BaseModel):
    event_id: str
    name: str
    city: str
    start_datetime: str
    end_datetime: str
    guest_count: int
    alcohol_service: bool
    food_products_count: int
    requirements: list[EventRequirementResponse]


class CandidateResponse(BaseModel):
    server_id: str
    name: str
    gender: str
    city: str
    experience_years: int
    worker_type: str
    main_skill_level: int
    availability_status: str
    distance_km: float | None
    score: float | None
    reasons: list[str]
    exclusion_reason: str | None = None
    role: str | None = None


class RequirementRecommendation(BaseModel):
    requirement: EventRequirementResponse
    candidates: list[CandidateResponse]
    selected: list[CandidateResponse]
    status: str
    message: str | None = None


class StaffRecommendationResponse(BaseModel):
    event: EventResponse
    requirements: list[RequirementRecommendation]
    total_eligible: int
    total_excluded: int
    total_selected: int
    status: str
