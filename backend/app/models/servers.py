from pydantic import BaseModel
from typing import Optional


class ServerSkillResponse(BaseModel):
    name: str
    level: int


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
    location: ServerLocationResponse
    skills: list[ServerSkillResponse]
    vehicle: Optional[ServerVehicleResponse] = None
    availability: list[ServerAvailabilityResponse]
    points: ServerPointsResponse


class ServerStatsResponse(BaseModel):
    total: int
    available: int
    unavailable: int
    with_vehicle: int
