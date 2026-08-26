import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"
STAFF_EMAIL = "staff@test.com"
STAFF_PASSWORD = "TestPassword123!"


def _admin_headers():
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _staff_headers():
    r = client.post("/api/auth/login", json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestEventDetailEndpoint:
    def test_event_detail_returns_200_with_valid_event(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "event" in data
        assert "staffing" in data
        assert "requirements" in data
        assert "assignments" in data
        assert "transport" in data

    def test_event_detail_requirements_have_requirement_id(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001", headers=headers)
        assert r.status_code == 200
        data = r.json()
        for req in data.get("requirements", []):
            assert "requirement_id" in req
            assert "role_name" in req
            assert "quantity" in req

    def test_event_detail_assignments_have_expected_fields(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001", headers=headers)
        assert r.status_code == 200
        data = r.json()
        for a in data.get("assignments", []):
            assert "server_id" in a
            assert "server_name" in a
            assert "role" in a
            assert "status" in a


class TestServerEndpoints:
    def test_server_list_returns_paginated_structure(self):
        headers = _admin_headers()
        r = client.get("/api/servers", headers=headers, params={"page_size": 10})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_server_list_handles_null_worker_type(self):
        server_id = "58ff93f6-7bdf-4fa2-9f7c-94374201a92e"
        headers = _admin_headers()
        r = client.get("/api/servers", headers=headers, params={"page_size": 100})
        assert r.status_code == 200
        data = r.json()
        server = next((s for s in data["items"] if s["id"] == server_id), None)
        assert server is not None
        assert server["worker_type"] == ""
        assert server["location_verified"] is False

    def test_server_detail_returns_200(self):
        headers = _admin_headers()
        r = client.get("/api/servers/10000001-0001-0001-0001-000000000001", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "10000001-0001-0001-0001-000000000001"
        assert "first_name" in data
        assert "last_name" in data


class TestEventEvaluationsEndpoint:
    def test_event_evaluations_returns_list(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001/evaluations", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_event_evaluations_structure(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001/evaluations", headers=headers)
        assert r.status_code == 200
        data = r.json()
        for ev in data:
            assert "id" in ev
            assert "server_id" in ev
            assert "punctuality" in ev
            assert "work_quality" in ev
            assert "presentation" in ev
            assert "teamwork" in ev
            assert "client_relation" in ev


class TestEventReportEndpoint:
    def test_event_report_returns_200(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001/report", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "event_id" in data
        assert "event_name" in data
        assert "final_kpis" in data
        assert "alerts" in data
        assert "generated_at" in data


class TestEventRequirementsEndpoint:
    def test_event_requirements_returns_list(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001/requirements", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "event_id" in data
        assert "requirements" in data
        for req in data.get("requirements", []):
            assert "requirement_id" in req
            assert "role_name" in req
            assert "quantity" in req


class TestTransportEndpoint:
    def test_recommend_transport_requires_manager(self):
        headers = _staff_headers()
        r = client.post("/api/events/50000001-0001-0001-0001-000000000001/recommend-transport", headers=headers)
        assert r.status_code == 403

    def test_recommend_transport_returns_expected_shape(self):
        headers = _admin_headers()
        r = client.post("/api/events/50000001-0001-0001-0001-000000000001/recommend-transport", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "event_id" in data
        assert "transport_status" in data
        assert "drivers" in data
        assert "passengers" in data
        assert "unassigned_passengers" in data
        assert "total_selected" in data
        assert "total_assigned" in data
        assert "total_unassigned" in data


class TestGamificationEndpoints:
    def test_award_completion_points_requires_manager(self):
        headers = _staff_headers()
        r = client.post("/api/events/50000001-0001-0001-0001-000000000001/award-completion-points", headers=headers)
        assert r.status_code == 403

    def test_award_performance_points_requires_manager(self):
        headers = _staff_headers()
        r = client.post("/api/events/50000001-0001-0001-0001-000000000001/award-performance-points", headers=headers)
        assert r.status_code == 403

    def test_server_points_returns_200(self):
        headers = _admin_headers()
        r = client.get("/api/servers/10000001-0001-0001-0001-000000000001/points", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "server_id" in data
        assert "total_points" in data
        assert "completion_points" in data
        assert "performance_points" in data

    def test_rankings_returns_200(self):
        headers = _admin_headers()
        r = client.get("/api/rankings/2025/1", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "year" in data
        assert "month" in data
        assert "rankings" in data
        assert "total_servers" in data
        assert "total_points" in data

    def test_bonuses_returns_200(self):
        headers = _admin_headers()
        r = client.get("/api/bonuses/2025/1", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


class TestUrgentStaffingEndpoint:
    def test_generate_urgent_offers_requires_manager(self):
        headers = _staff_headers()
        r = client.post("/api/events/50000001-0001-0001-0001-000000000001/urgent-offers/generate", headers=headers)
        assert r.status_code == 403

    def test_generate_urgent_offers_requires_urgent_event(self):
        headers = _admin_headers()
        r = client.post("/api/events/50000001-0001-0001-0001-000000000001/urgent-offers/generate", headers=headers)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data

    def test_urgent_status_returns_200_for_non_urgent_event(self):
        headers = _admin_headers()
        r = client.get("/api/events/50000001-0001-0001-0001-000000000001/urgent-status", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "event_id" in data
        assert "is_urgent" in data
        assert data["is_urgent"] is False

    def test_urgent_status_returns_404_for_invalid_event(self):
        headers = _admin_headers()
        r = client.get("/api/events/00000000-0000-0000-0000-000000000000/urgent-status", headers=headers)
        assert r.status_code == 404
