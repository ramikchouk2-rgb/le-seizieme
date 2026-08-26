from pydantic import BaseModel
from typing import Optional, Any


class UrgentOfferResponse(BaseModel):
    offer_id: str
    server_id: str
    server_name: str
    role: str
    status: str
    wave_number: int
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    score: Optional[float] = None
    distance_km: Optional[float] = None
    reason: Optional[str] = None


class UrgentStatusResponse(BaseModel):
    event_id: str
    is_urgent: bool
    wave_number: int = 0
    wave_size: int = 0
    offers_sent: int = 0
    pending_count: int = 0
    accepted_count: int = 0
    declined_count: int = 0
    expired_count: int = 0
    total_staff_needed: int = 0
    total_staff_confirmed: int = 0
    remaining_staff: int = 0
    can_generate_next_wave: bool = False
    offers: list[UrgentOfferResponse] = []
    requirements: list[dict[str, Any]] = []


class UrgentGenerateResponse(BaseModel):
    event_id: str
    status: str
    wave_number: int
    offers_created: int
    requirements: list[dict[str, Any]] = []
    offers: list[UrgentOfferResponse] = []


class UrgentActionResponse(BaseModel):
    success: bool
    message: str
    offer: Optional[dict[str, Any]] = None
    urgent_status: Optional[dict[str, Any]] = None
