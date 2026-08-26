from pydantic import BaseModel
from typing import Optional


class TransportPassengerConfirmation(BaseModel):
    server_id: str
    pickup_order: int


class TransportGroupConfirmation(BaseModel):
    driver_server_id: str
    passengers: list[TransportPassengerConfirmation]


class TransportConfirmationRequest(BaseModel):
    groups: list[TransportGroupConfirmation]


class TransportConfirmationGroupResponse(BaseModel):
    group_id: str
    driver_name: str
    vehicle: str
    capacity: int
    passenger_count: int
    estimated_distance_km: float | None = None


class TransportConfirmationResponse(BaseModel):
    event_id: str
    status: str
    groups_created: int
    passengers_created: int
    groups: list[TransportConfirmationGroupResponse]
    message: str | None = None


class TransportDriverResponse(BaseModel):
    server_id: str
    name: str
    vehicle: str
    capacity: int
    available_seats: int
    can_transport_coworkers: bool


class TransportPassengerResponse(BaseModel):
    server_id: str
    name: str
    pickup_order: int
    distance_from_driver_km: float


class TransportUnassignedPassengerResponse(BaseModel):
    server_id: str
    name: str
    reason: str


class TransportRecommendationResponse(BaseModel):
    event_id: str
    transport_status: str
    drivers: list[TransportDriverResponse]
    passengers: list[TransportPassengerResponse]
    unassigned_passengers: list[TransportUnassignedPassengerResponse]
    total_selected: int
    total_assigned: int
    total_unassigned: int
