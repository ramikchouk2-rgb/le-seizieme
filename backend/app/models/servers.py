from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class ServerSkillResponse(BaseModel):
    skill_id: str
    name: str
    level: int
    years_experience: int


class ServerVehicleResponse(BaseModel):
    id: str
    vehicle_type: str
    brand: str
    model: str
    seats_total: int
    can_transport_coworkers: bool
    is_active: bool


class ServerAvailabilityResponse(BaseModel):
    id: str
    start_datetime: str
    end_datetime: str
    status: str


class ServerPointsResponse(BaseModel):
    total_points: int
    current_month_points: int
    previous_month_points: int
    rank: Optional[int] = None


class ServerListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    gender: str
    city: str
    years_experience: int
    worker_type: str
    availability_status: str
    main_skill: str
    main_skill_level: int
    vehicle: Optional[dict] = None
    location_verified: bool
    monthly_points: int
    rank: int


class ServerListResponse(BaseModel):
    items: list[ServerListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ServerLocationResponse(BaseModel):
    city: str
    area: str
    is_verified: bool


class ServerSkillCreateRequest(BaseModel):
    skill_id: str
    level: int
    years_experience: int = 0

    @field_validator('level')
    @classmethod
    def level_must_be_1_to_10(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Le niveau de compétence doit être entre 1 et 10.')
        return v


class ServerSkillUpdateRequest(BaseModel):
    level: Optional[int] = None
    years_experience: Optional[int] = None

    @field_validator('level')
    @classmethod
    def level_must_be_1_to_10(cls, v):
        if v is not None and not 1 <= v <= 10:
            raise ValueError('Le niveau de compétence doit être entre 1 et 10.')
        return v


class ServerVehicleResponse(BaseModel):
    id: str
    vehicle_type: str
    brand: str
    model: str
    seats_total: int
    can_transport_coworkers: bool
    is_active: bool


class ServerVehicleCreateRequest(BaseModel):
    vehicle_type: str
    brand: str
    model: str
    seats_total: int
    can_transport_coworkers: bool = False


class ServerVehicleUpdateRequest(BaseModel):
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    seats_total: Optional[int] = None
    can_transport_coworkers: Optional[bool] = None
    is_active: Optional[bool] = None


class ServerAvailabilityResponse(BaseModel):
    id: str
    start_datetime: str
    end_datetime: str
    status: str


class ServerAvailabilityCreateRequest(BaseModel):
    start_datetime: datetime
    end_datetime: datetime
    status: str = "AVAILABLE"
    note: Optional[str] = None


class ServerAvailabilityUpdateRequest(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status: Optional[str] = None
    note: Optional[str] = None


class ServerAvailabilityListResponse(BaseModel):
    items: list[ServerAvailabilityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ServerPointsResponse(BaseModel):
    total_points: int
    current_month_points: int
    previous_month_points: int
    rank: Optional[int] = None


class ServerListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    gender: str
    city: str
    years_experience: int
    worker_type: str
    availability_status: str
    main_skill: str
    main_skill_level: int
    vehicle: Optional[dict] = None
    location_verified: bool
    monthly_points: int
    rank: int


class ServerListResponse(BaseModel):
    items: list[ServerListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ServerLocationResponse(BaseModel):
    city: str
    area: str
    is_verified: bool


class ServerProfileResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    gender: str
    city: str
    years_experience: int
    worker_type: str
    availability_status: str
    email: str
    phone: str
    location: dict
    skills: list
    vehicle: Optional[ServerVehicleResponse] = None
    availability: list[ServerAvailabilityResponse]
    points: dict


class ServerStatsResponse(BaseModel):
    total: int
    available: int
    unavailable: int
    with_vehicle: int


class ServerCreateRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    gender: str
    city_id: str
    years_experience: int = 0
    worker_type: Optional[str] = None
    speed_score: int = 5
    punctuality_score: int = 5
    presentation_score: int = 5
    communication_score: int = 5
    teamwork_score: int = 5
    discipline_score: int = 5
    endurance_score: int = 5


class ServerUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    city_id: Optional[str] = None
    years_experience: Optional[int] = None
    worker_type: Optional[str] = None
    speed_score: Optional[int] = None
    punctuality_score: Optional[int] = None
    presentation_score: Optional[int] = None
    communication_score: Optional[int] = None
    teamwork_score: Optional[int] = None
    discipline_score: Optional[int] = None
    endurance_score: Optional[int] = None
    is_active: Optional[bool] = None


class ServerResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    gender: str
    city_id: str
    years_experience: int
    worker_type: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
