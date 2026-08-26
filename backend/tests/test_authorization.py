import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"
MANAGER_EMAIL = "manager@test.com"
MANAGER_PASSWORD = "TestPassword123!"
STAFF_EMAIL = "staff@test.com"
STAFF_PASSWORD = "TestPassword123!"


def _login(client: AsyncClient, email: str, password: str) -> str:
    import asyncio

    async def _do_login():
        r = await client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, f"Login failed for {email}: {r.text}"
        return r.json()["access_token"]

    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _do_login())
            return future.result()
    else:
        return loop.run_until_complete(_do_login())


class TestAuthorizationMatrix:
    async def test_unauthenticated_events_list_returns_401(self, client: AsyncClient):
        r = await client.get("/api/events")
        assert r.status_code == 401

    async def test_unauthenticated_events_detail_returns_401(self, client: AsyncClient):
        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001")
        assert r.status_code == 401

    async def test_unauthenticated_cities_returns_401(self, client: AsyncClient):
        r = await client.get("/api/cities")
        assert r.status_code == 401

    async def test_unauthenticated_servers_list_returns_401(self, client: AsyncClient):
        r = await client.get("/api/servers")
        assert r.status_code == 401

    async def test_unauthenticated_servers_detail_returns_401(self, client: AsyncClient):
        r = await client.get("/api/servers/00000000-0000-0000-0000-000000000002")
        assert r.status_code == 401

    async def test_unauthenticated_attendance_returns_401(self, client: AsyncClient):
        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001/attendance")
        assert r.status_code == 401

    async def test_unauthenticated_operations_returns_401(self, client: AsyncClient):
        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001/operations")
        assert r.status_code == 401

    async def test_unauthenticated_report_returns_401(self, client: AsyncClient):
        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001/report")
        assert r.status_code == 401

    async def test_unauthenticated_evaluations_returns_401(self, client: AsyncClient):
        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001/evaluations")
        assert r.status_code == 401

    async def test_unauthenticated_requirements_returns_401(self, client: AsyncClient):
        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001/requirements")
        assert r.status_code == 401

    async def test_unauthenticated_staff_mutation_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/staff", json={})
        assert r.status_code == 401

    async def test_unauthenticated_status_update_returns_401(self, client: AsyncClient):
        r = await client.patch(
            "/api/events/00000000-0000-0000-0000-000000000001/status",
            json={"status": "CANCELLED"},
        )
        assert r.status_code == 401

    async def test_unauthenticated_create_event_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events", json={})
        assert r.status_code == 401

    async def test_unauthenticated_confirm_staff_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/confirm-staff", json=[])
        assert r.status_code == 401

    async def test_unauthenticated_generate_staff_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/generate-staff")
        assert r.status_code == 401

    async def test_unauthenticated_transport_recommend_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/recommend-transport")
        assert r.status_code == 401

    async def test_unauthenticated_transport_confirm_returns_401(self, client: AsyncClient):
        r = await client.post(
            "/api/events/00000000-0000-0000-0000-000000000001/confirm-transport",
            json={"groups": []},
        )
        assert r.status_code == 401

    async def test_unauthenticated_urgent_generate_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/urgent-offers/generate")
        assert r.status_code == 401

    async def test_unauthenticated_award_completion_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/award-completion-points")
        assert r.status_code == 401

    async def test_unauthenticated_award_performance_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/award-performance-points")
        assert r.status_code == 401

    async def test_unauthenticated_calculate_rankings_returns_401(self, client: AsyncClient):
        r = await client.post("/api/rankings/2024/1/calculate")
        assert r.status_code == 401

    async def test_unauthenticated_rankings_returns_401(self, client: AsyncClient):
        r = await client.get("/api/rankings/2024/1")
        assert r.status_code == 401

    async def test_unauthenticated_bonuses_returns_401(self, client: AsyncClient):
        r = await client.get("/api/bonuses/2024/1")
        assert r.status_code == 401

    async def test_unauthenticated_availability_create_returns_401(self, client: AsyncClient):
        r = await client.post("/api/servers/00000000-0000-0000-0000-000000000002/availability", json={})
        assert r.status_code == 401

    async def test_unauthenticated_availability_delete_returns_401(self, client: AsyncClient):
        r = await client.delete("/api/servers/00000000-0000-0000-0000-000000000002/availability/00000000-0000-0000-0000-000000000003")
        assert r.status_code == 401

    async def test_unauthenticated_attendance_initialize_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/attendance/initialize")
        assert r.status_code == 401

    async def test_unauthenticated_attendance_checkin_returns_401(self, client: AsyncClient):
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/attendance/00000000-0000-0000-0000-000000000004/check-in")
        assert r.status_code == 401

    async def test_unauthenticated_activity_returns_401(self, client: AsyncClient):
        r = await client.get("/api/activity/recent")
        assert r.status_code == 401

    async def test_admin_can_access_protected_endpoints(self, client: AsyncClient, admin_token: str):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = await client.get("/api/events", headers=headers)
        assert r.status_code == 200

        r = await client.get("/api/cities", headers=headers)
        assert r.status_code == 200

        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001", headers=headers)
        assert r.status_code in (200, 404)

    async def test_manager_can_access_manager_endpoints(self, client: AsyncClient, manager_token: str):
        headers = {"Authorization": f"Bearer {manager_token}"}
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/urgent-offers/generate", headers=headers)
        assert r.status_code in (200, 400, 404)

    async def test_manager_can_access_rankings_calculate(self, client: AsyncClient, manager_token: str):
        headers = {"Authorization": f"Bearer {manager_token}"}
        r = await client.post("/api/rankings/2024/1/calculate", headers=headers)
        assert r.status_code == 200

    async def test_staff_cannot_access_manager_mutation_endpoints(self, client: AsyncClient, staff_token: str):
        headers = {"Authorization": f"Bearer {staff_token}"}
        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/urgent-offers/generate", headers=headers)
        assert r.status_code == 403

        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/confirm-staff", json=[], headers=headers)
        assert r.status_code == 403

        r = await client.post("/api/events/00000000-0000-0000-0000-000000000001/recommend-transport", headers=headers)
        assert r.status_code == 403

    async def test_staff_can_read_protected_list_endpoints(self, client: AsyncClient, staff_token: str):
        headers = {"Authorization": f"Bearer {staff_token}"}
        r = await client.get("/api/events", headers=headers)
        assert r.status_code == 200

        r = await client.get("/api/cities", headers=headers)
        assert r.status_code == 200

        r = await client.get("/api/events/00000000-0000-0000-0000-000000000001/evaluations", headers=headers)
        assert r.status_code in (200, 404)
