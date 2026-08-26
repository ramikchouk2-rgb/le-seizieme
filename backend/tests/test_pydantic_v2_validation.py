import pytest
from pydantic import ValidationError

from app.models.events import (
    RequirementCreateRequest,
    RequirementUpdateRequest,
    EventStatusUpdateRequest,
)
from app.models.assignment import (
    AddStaffAssignmentRequest,
    UpdateStaffAssignmentRequest,
)
from app.models.evaluations import (
    EvaluationCreateRequest,
    EvaluationUpdateRequest,
)
from app.models.attendance import AttendanceStatusUpdateRequest
from app.models.availability import (
    AvailabilityCreateRequest,
    AvailabilityUpdateRequest,
)


class TestRequirementCreateRequest:
    def test_valid_payload(self):
        payload = RequirementCreateRequest(
            role_name="SERVER",
            quantity=2,
            minimum_skill_level=5,
            minimum_experience=3,
            required_gender="MALE",
        )
        assert payload.quantity == 2
        assert payload.minimum_skill_level == 5
        assert payload.minimum_experience == 3
        assert payload.required_gender == "MALE"

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError) as exc:
            RequirementCreateRequest(role_name="SERVER", quantity=0)
        assert "La quantité doit être au moins 1" in str(exc.value)

    def test_skill_level_bounds(self):
        with pytest.raises(ValidationError):
            RequirementCreateRequest(role_name="SERVER", quantity=1, minimum_skill_level=0)
        with pytest.raises(ValidationError):
            RequirementCreateRequest(role_name="SERVER", quantity=1, minimum_skill_level=11)

    def test_experience_non_negative(self):
        with pytest.raises(ValidationError):
            RequirementCreateRequest(role_name="SERVER", quantity=1, minimum_experience=-1)

    def test_gender_validation(self):
        with pytest.raises(ValidationError):
            RequirementCreateRequest(role_name="SERVER", quantity=1, required_gender="INVALID")


class TestRequirementUpdateRequest:
    def test_valid_partial_payload(self):
        payload = RequirementUpdateRequest(quantity=5)
        assert payload.quantity == 5
        assert payload.minimum_skill_level is None

    def test_optional_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            RequirementUpdateRequest(quantity=0)

    def test_skill_level_bounds_optional(self):
        with pytest.raises(ValidationError):
            RequirementUpdateRequest(minimum_skill_level=0)

    def test_experience_non_negative_optional(self):
        with pytest.raises(ValidationError):
            RequirementUpdateRequest(minimum_experience=-1)

    def test_gender_validation_optional(self):
        with pytest.raises(ValidationError):
            RequirementUpdateRequest(required_gender="INVALID")


class TestEventStatusUpdateRequest:
    def test_valid_status(self):
        for status in ("PLANNED", "STAFFING", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED"):
            payload = EventStatusUpdateRequest(status=status)
            assert payload.status == status

    def test_invalid_status(self):
        with pytest.raises(ValidationError) as exc:
            EventStatusUpdateRequest(status="INVALID")
        assert "Statut invalide" in str(exc.value)


class TestAddStaffAssignmentRequest:
    def test_valid_payload(self):
        payload = AddStaffAssignmentRequest(
            server_id="abc-123",
            requirement_id="req-456",
            role="SERVER",
        )
        assert payload.server_id == "abc-123"
        assert payload.requirement_id == "req-456"
        assert payload.role == "SERVER"

    def test_server_id_required(self):
        with pytest.raises(ValidationError):
            AddStaffAssignmentRequest(server_id="", requirement_id="req-456", role="SERVER")

    def test_requirement_id_required(self):
        with pytest.raises(ValidationError):
            AddStaffAssignmentRequest(server_id="abc-123", requirement_id="", role="SERVER")

    def test_role_required_and_stripped(self):
        payload = AddStaffAssignmentRequest(server_id="abc-123", requirement_id="req-456", role="  SERVER  ")
        assert payload.role == "SERVER"

    def test_role_cannot_be_blank(self):
        with pytest.raises(ValidationError):
            AddStaffAssignmentRequest(server_id="abc-123", requirement_id="req-456", role="   ")


class TestUpdateStaffAssignmentRequest:
    def test_valid_payload(self):
        payload = UpdateStaffAssignmentRequest(role="BARMAN", assignment_status="CONFIRMED")
        assert payload.role == "BARMAN"
        assert payload.assignment_status == "CONFIRMED"

    def test_role_cannot_be_blank(self):
        with pytest.raises(ValidationError):
            UpdateStaffAssignmentRequest(role="   ")

    def test_invalid_assignment_status(self):
        with pytest.raises(ValidationError):
            UpdateStaffAssignmentRequest(assignment_status="INVALID")

    def test_optional_fields_default_to_none(self):
        payload = UpdateStaffAssignmentRequest()
        assert payload.role is None
        assert payload.assignment_status is None
        assert payload.requirement_id is None


class TestEvaluationCreateRequest:
    def test_valid_payload(self):
        payload = EvaluationCreateRequest(
            server_id="srv-1",
            punctuality=8,
            work_quality=9,
            presentation=7,
            teamwork=10,
            client_relation=6,
        )
        assert payload.punctuality == 8
        assert payload.work_quality == 9

    def test_score_below_1_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationCreateRequest(
                server_id="srv-1",
                punctuality=0,
                work_quality=5,
                presentation=5,
                teamwork=5,
                client_relation=5,
            )

    def test_score_above_10_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationCreateRequest(
                server_id="srv-1",
                punctuality=11,
                work_quality=5,
                presentation=5,
                teamwork=5,
                client_relation=5,
            )


class TestEvaluationUpdateRequest:
    def test_valid_partial_payload(self):
        payload = EvaluationUpdateRequest(punctuality=7, comment="Great")
        assert payload.punctuality == 7
        assert payload.work_quality is None

    def test_score_below_1_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationUpdateRequest(punctuality=0)

    def test_score_above_10_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationUpdateRequest(punctuality=11)


class TestAttendanceStatusUpdateRequest:
    def test_valid_status(self):
        for status in ("EXPECTED", "PRESENT", "LATE", "ABSENT", "EXCUSED", "LEFT"):
            payload = AttendanceStatusUpdateRequest(status=status)
            assert payload.status == status

    def test_invalid_status(self):
        with pytest.raises(ValidationError) as exc:
            AttendanceStatusUpdateRequest(status="INVALID")
        assert "Statut invalide" in str(exc.value)


class TestAvailabilityCreateRequest:
    def test_valid_payload(self):
        payload = AvailabilityCreateRequest(
            start_datetime="2025-01-01T08:00:00",
            end_datetime="2025-01-01T17:00:00",
            status="AVAILABLE",
        )
        assert payload.start_datetime == "2025-01-01T08:00:00"
        assert payload.end_datetime == "2025-01-01T17:00:00"

    def test_start_datetime_required(self):
        with pytest.raises(ValidationError):
            AvailabilityCreateRequest(start_datetime="", end_datetime="2025-01-01T17:00:00")

    def test_end_datetime_required(self):
        with pytest.raises(ValidationError):
            AvailabilityCreateRequest(start_datetime="2025-01-01T08:00:00", end_datetime="")

    def test_end_must_be_after_start(self):
        with pytest.raises(ValidationError) as exc:
            AvailabilityCreateRequest(
                start_datetime="2025-01-01T17:00:00",
                end_datetime="2025-01-01T08:00:00",
            )
        assert "end_datetime doit être supérieur" in str(exc.value)

    def test_valid_status_values(self):
        for status in ("AVAILABLE", "UNAVAILABLE", "RESERVED"):
            payload = AvailabilityCreateRequest(
                start_datetime="2025-01-01T08:00:00",
                end_datetime="2025-01-01T17:00:00",
                status=status,
            )
            assert payload.status == status

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            AvailabilityCreateRequest(
                start_datetime="2025-01-01T08:00:00",
                end_datetime="2025-01-01T17:00:00",
                status="INVALID",
            )


class TestAvailabilityUpdateRequest:
    def test_valid_partial_payload(self):
        payload = AvailabilityUpdateRequest(status="UNAVAILABLE")
        assert payload.status == "UNAVAILABLE"
        assert payload.start_datetime is None

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            AvailabilityUpdateRequest(status="INVALID")

    def test_end_must_be_after_start_when_both_provided(self):
        with pytest.raises(ValidationError) as exc:
            AvailabilityUpdateRequest(
                start_datetime="2025-01-01T17:00:00",
                end_datetime="2025-01-01T08:00:00",
            )
        assert "end_datetime doit être supérieur" in str(exc.value)

    def test_single_datetime_update_allowed(self):
        payload = AvailabilityUpdateRequest(start_datetime="2025-01-01T08:00:00")
        assert payload.start_datetime == "2025-01-01T08:00:00"
        assert payload.end_datetime is None
