import pytest
from pydantic import ValidationError

from app.models.events import (
    CityResponse,
    DeleteResponse,
    EventDetailEventResponse,
    EventDetailStaffingResponse,
    EventDetailTransportGroupResponse,
    EventDetailTransportResponse,
    EventDetailResponse,
    EventRequirementsResponse,
    EventRequirementDetailResponse,
)
from app.models.attendance import AttendanceActionResponse
from app.models.transport_assignment import (
    TransportDriverResponse,
    TransportPassengerResponse,
    TransportUnassignedPassengerResponse,
    TransportRecommendationResponse,
)
from app.models.health import PingResponse


class TestCityResponse:
    def test_valid_city(self):
        city = CityResponse(id="abc-123", name="Paris")
        assert city.id == "abc-123"
        assert city.name == "Paris"

    def test_id_must_be_string(self):
        with pytest.raises(ValidationError):
            CityResponse(id=123, name="Paris")


class TestDeleteResponse:
    def test_valid_delete(self):
        resp = DeleteResponse(deleted=True)
        assert resp.deleted is True

    def test_default_deleted(self):
        resp = DeleteResponse()
        assert resp.deleted is True


class TestEventDetailResponse:
    def test_valid_event_detail(self):
        event_detail = EventDetailResponse(
            event=EventDetailEventResponse(
                id="e1",
                name="Test Event",
                city="Paris",
                start_datetime="2025-01-01T08:00:00",
                end_datetime="2025-01-01T17:00:00",
                guest_count=50,
                alcohol_service=False,
                food_products_count=10,
                priority="NORMAL",
                urgent=False,
                status="PLANNED",
            ),
            staffing=EventDetailStaffingResponse(
                requested=10,
                selected=8,
                missing=2,
                percentage=80,
            ),
            requirements=[
                EventRequirementDetailResponse(
                    requirement_id="r1",
                    role_name="SERVER",
                    quantity=5,
                    required_gender="MALE",
                    minimum_experience=2,
                    minimum_skill_level=3,
                    selected=3,
                    missing=2,
                )
            ],
            assignments=[
                {
                    "id": "a1",
                    "server_id": "s1",
                    "server_name": "John Doe",
                    "gender": "MALE",
                    "city": "Paris",
                    "role": "SERVER",
                    "required_gender": "MALE",
                    "score": 85.5,
                    "distance_km": 12.3,
                    "years_experience": 5,
                    "skill_level": 4,
                    "availability_status": "AVAILABLE",
                    "status": "CONFIRMED",
                    "reasons": ["Good match"],
                }
            ],
            transport=EventDetailTransportResponse(
                groups=[
                    EventDetailTransportGroupResponse(
                        group_id="g1",
                        driver_server_id="s2",
                        driver_name="Jane Doe",
                        vehicle="Toyota Corolla",
                        capacity=5,
                        passenger_count=3,
                        estimated_distance_km=25.5,
                        passengers=[
                            {
                                "server_id": "s3",
                                "name": "Bob Smith",
                                "pickup_order": 1,
                                "pickup_status": "PENDING",
                                "distance_km": None,
                            }
                        ],
                        status="CONFIRMED",
                    )
                ],
                total_groups=1,
                total_passengers=3,
            ),
        )
        assert event_detail.event.id == "e1"
        assert event_detail.staffing.percentage == 80
        assert len(event_detail.requirements) == 1
        assert len(event_detail.assignments) == 1
        assert len(event_detail.transport.groups) == 1


class TestEventRequirementsResponse:
    def test_valid_requirements(self):
        resp = EventRequirementsResponse(
            event_id="e1",
            requirements=[
                EventRequirementDetailResponse(
                    requirement_id="r1",
                    role_name="BARMAN",
                    quantity=2,
                    required_gender=None,
                    minimum_experience=1,
                    minimum_skill_level=5,
                    selected=1,
                    missing=1,
                )
            ],
        )
        assert resp.event_id == "e1"
        assert len(resp.requirements) == 1


class TestAttendanceActionResponse:
    def test_check_in_response(self):
        resp = AttendanceActionResponse(
            success=True,
            attendance_id="att-123",
            message="Check-in enregistré.",
        )
        assert resp.success is True
        assert resp.attendance_id == "att-123"
        assert resp.status is None

    def test_status_update_response(self):
        resp = AttendanceActionResponse(
            success=True,
            attendance_id="att-123",
            message="Status updated.",
            status="PRESENT",
        )
        assert resp.status == "PRESENT"


class TestTransportRecommendationResponse:
    def test_valid_recommendation(self):
        resp = TransportRecommendationResponse(
            event_id="e1",
            transport_status="SUCCESS",
            drivers=[
                TransportDriverResponse(
                    server_id="s1",
                    name="Driver One",
                    vehicle="Toyota Corolla",
                    capacity=5,
                    available_seats=4,
                    can_transport_coworkers=True,
                )
            ],
            passengers=[
                TransportPassengerResponse(
                    server_id="s2",
                    name="Passenger One",
                    pickup_order=1,
                    distance_from_driver_km=3.5,
                )
            ],
            unassigned_passengers=[
                TransportUnassignedPassengerResponse(
                    server_id="s3",
                    name="Passenger Two",
                    reason="Outside pickup radius",
                )
            ],
            total_selected=3,
            total_assigned=1,
            total_unassigned=2,
        )
        assert resp.transport_status == "SUCCESS"
        assert len(resp.drivers) == 1
        assert len(resp.passengers) == 1
        assert len(resp.unassigned_passengers) == 1
        assert resp.total_assigned == 1


class TestPingResponse:
    def test_valid_ping(self):
        resp = PingResponse(message="pong")
        assert resp.message == "pong"
