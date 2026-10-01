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
    # Sum of the driver-to-passenger legs plus the final venue leg. Same meaning
    # as in the confirmation response, which is where it is persisted.
    estimated_distance_km: float | None = None
    # Step 24C-D-4: true end-to-end itinerary distance, computed the same way
    # as the recommendation endpoint. Prefer this for display.
    estimated_route_distance_km: float | None = None
    has_exact_location: bool = True


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


class TransportRecommendationGroupResponse(BaseModel):
    """Step 24C-D-4: a per-driver group, previously computed and then discarded.

    The recommendation used to expose only flat driver/passenger lists, so the
    venue leg was invisible and the two endpoints could not be compared.
    """

    driver: TransportDriverResponse
    passengers: list[TransportPassengerResponse]
    estimated_passenger_count: int
    estimated_distance_km: float | None = None
    estimated_route_distance_km: float | None = None
    has_exact_location: bool = True


class TransportRecommendationResponse(BaseModel):
    event_id: str
    transport_status: str
    # False when the venue leg used the city reference or the global technical
    # fallback rather than the event's own coordinates.
    has_exact_location: bool = True
    drivers: list[TransportDriverResponse]
    passengers: list[TransportPassengerResponse]
    unassigned_passengers: list[TransportUnassignedPassengerResponse]
    groups: list[TransportRecommendationGroupResponse] = []
    total_selected: int
    total_assigned: int
    total_unassigned: int
