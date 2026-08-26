import uuid
from datetime import datetime

import pytest

from app.main import app
from app.core.database import get_pool
from app.services.event_service import (
    confirm_staff_assignments,
    delete_requirement,
    remove_staff_assignment,
    update_requirement,
    update_staff_assignment,
)

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"


def _admin_headers():
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_test_server_direct():
    server_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO servers (id, first_name, last_name, phone, email, gender, city_id, years_experience, is_active)
            VALUES ($1, $2, $3, $4, $5, 'MALE', (SELECT id FROM cities LIMIT 1), $6, TRUE)
            """,
            server_id,
            "Test",
            "Server",
            "1234567890",
            f"testserver-{server_id}@test.com",
            5,
        )
        await conn.execute(
            """
            INSERT INTO server_skills (server_id, skill_id, level, years_experience)
            VALUES ($1, (SELECT id FROM skills WHERE name = 'Service à table' LIMIT 1), $2, $3)
            """,
            server_id,
            5,
            2,
        )
    return str(server_id)


async def _create_test_event_direct(status="STAFFING", start_hour=10, end_hour=12):
    event_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO events (id, name, client_name, city_id, address, start_datetime, end_datetime, guest_count, event_type, status)
            VALUES ($1, $2, $3, (SELECT id FROM cities LIMIT 1), $4, $5, $6, $7, $8, $9)
            """,
            event_id,
            f"Test Event {event_id}",
            "Test Client",
            "123 Test Street",
            datetime(2025, 1, 15, start_hour, 0, 0),
            datetime(2025, 1, 15, end_hour, 0, 0),
            10,
            "TEST",
            status,
        )
    return str(event_id)


async def _create_test_requirement_direct(event_id, role_name="Service à table", quantity=1):
    req_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_requirements (id, event_id, role_name, quantity, minimum_skill_level, minimum_experience, required_gender)
            VALUES ($1, $2, $3, $4, $5, $6, NULL)
            """,
            req_id,
            event_id,
            role_name,
            quantity,
            1,
            0,
        )
    return str(req_id)


async def _add_availability(server_id, start_hour=8, end_hour=14):
    avail_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO server_availability (id, server_id, start_datetime, end_datetime, status)
            VALUES ($1, $2, $3, $4, 'AVAILABLE')
            """,
            avail_id,
            server_id,
            datetime(2025, 1, 15, start_hour, 0, 0),
            datetime(2025, 1, 15, end_hour, 0, 0),
        )
    return str(avail_id)


async def _get_assignment_id(event_id, server_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM event_staff WHERE event_id = $1 AND server_id = $2",
            event_id,
            server_id,
        )
        return str(row["id"]) if row else None


async def _cleanup_event(event_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM event_attendance WHERE event_id = $1", event_id)
        await conn.execute("DELETE FROM event_staff WHERE event_id = $1", event_id)
        await conn.execute("DELETE FROM event_requirements WHERE event_id = $1", event_id)
        await conn.execute("DELETE FROM events WHERE id = $1", event_id)


async def _cleanup_server(server_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM server_availability WHERE server_id = $1", server_id)
        await conn.execute("DELETE FROM server_skills WHERE server_id = $1", server_id)
        await conn.execute("DELETE FROM event_staff WHERE server_id = $1", server_id)
        await conn.execute("DELETE FROM servers WHERE id = $1", server_id)


class TestDataIntegrity:
    async def test_confirmed_staff_cannot_be_removed(self):
        server_id = await _create_test_server_direct()
        event_id = await _create_test_event_direct(status="CONFIRMED")
        req_id = await _create_test_requirement_direct(event_id)
        await _add_availability(server_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-staff",
                json={"assignments": [{"server_id": server_id, "requirement_id": req_id, "role": "Service à table"}]},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Confirm failed: {r.text}"
            assignment_id = await _get_assignment_id(event_id, server_id)
            assert assignment_id is not None

            r = client.delete(
                f"/api/events/{event_id}/staff/{assignment_id}",
                headers=_admin_headers(),
            )
            assert r.status_code == 409
        finally:
            await _cleanup_event(event_id)
            await _cleanup_server(server_id)

    async def test_confirmed_staff_cannot_be_updated(self):
        server_id = await _create_test_server_direct()
        event_id = await _create_test_event_direct(status="CONFIRMED")
        req_id = await _create_test_requirement_direct(event_id)
        await _add_availability(server_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-staff",
                json={"assignments": [{"server_id": server_id, "requirement_id": req_id, "role": "Service à table"}]},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Confirm failed: {r.text}"
            assignment_id = await _get_assignment_id(event_id, server_id)
            assert assignment_id is not None

            r = client.patch(
                f"/api/events/{event_id}/staff/{assignment_id}",
                json={"assignment_status": "DECLINED"},
                headers=_admin_headers(),
            )
            assert r.status_code == 409
        finally:
            await _cleanup_event(event_id)
            await _cleanup_server(server_id)

    async def test_direct_confirmed_status_blocked(self):
        server_id = await _create_test_server_direct()
        event_id = await _create_test_event_direct(status="STAFFING")
        req_id = await _create_test_requirement_direct(event_id)
        await _add_availability(server_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/staff",
                json={"server_id": server_id, "requirement_id": req_id, "role": "Service à table"},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Add staff failed: {r.text}"
            assignment_id = r.json()["id"]

            r = client.patch(
                f"/api/events/{event_id}/staff/{assignment_id}",
                json={"assignment_status": "CONFIRMED"},
                headers=_admin_headers(),
            )
            assert r.status_code == 400
            assert "confirmation" in r.json()["detail"].lower() or "direct" in r.json()["detail"].lower()
        finally:
            await _cleanup_event(event_id)
            await _cleanup_server(server_id)

    async def test_completed_event_blocks_staff_mutations(self):
        server_id = await _create_test_server_direct()
        event_id = await _create_test_event_direct(status="COMPLETED")
        req_id = await _create_test_requirement_direct(event_id)
        await _add_availability(server_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/staff",
                json={"server_id": server_id, "requirement_id": req_id, "role": "Service à table"},
                headers=_admin_headers(),
            )
            assert r.status_code == 400
        finally:
            await _cleanup_event(event_id)
            await _cleanup_server(server_id)

    async def test_cancelled_event_blocks_requirement_update(self):
        event_id = await _create_test_event_direct(status="CANCELLED")
        req_id = await _create_test_requirement_direct(event_id)
        try:
            r = client.patch(
                f"/api/events/{event_id}/requirements/{req_id}",
                json={"quantity": 2},
                headers=_admin_headers(),
            )
            assert r.status_code == 400
        finally:
            await _cleanup_event(event_id)

    async def test_cancelled_event_blocks_requirement_delete(self):
        event_id = await _create_test_event_direct(status="CANCELLED")
        req_id = await _create_test_requirement_direct(event_id)
        try:
            r = client.delete(
                f"/api/events/{event_id}/requirements/{req_id}",
                headers=_admin_headers(),
            )
            assert r.status_code == 400
        finally:
            await _cleanup_event(event_id)

    async def test_attendance_initialized_for_confirmed_only(self):
        server_id = await _create_test_server_direct()
        event_id = await _create_test_event_direct(status="CONFIRMED")
        req_id = await _create_test_requirement_direct(event_id)
        await _add_availability(server_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-staff",
                json={"assignments": [{"server_id": server_id, "requirement_id": req_id, "role": "Service à table"}]},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Confirm failed: {r.text}"

            r = client.post(
                f"/api/events/{event_id}/attendance/initialize",
                headers=_admin_headers(),
            )
            assert r.status_code == 200

            r = client.get(f"/api/events/{event_id}/attendance", headers=_admin_headers())
            assert r.status_code == 200
            assert len(r.json()["staff"]) == 1
        finally:
            await _cleanup_event(event_id)
            await _cleanup_server(server_id)

    async def test_availability_delete_blocks_confirmed_event(self):
        server_id = await _create_test_server_direct()
        event_id = await _create_test_event_direct(status="CONFIRMED", start_hour=10, end_hour=11)
        req_id = await _create_test_requirement_direct(event_id)
        overlapping_avail_id = await _add_availability(server_id, start_hour=9, end_hour=12)
        await _add_availability(server_id, start_hour=8, end_hour=9)
        try:
            r = client.post(
                f"/api/events/{event_id}/staff",
                json={"server_id": server_id, "requirement_id": req_id, "role": "Service à table"},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Add staff failed: {r.text}"

            r = client.delete(
                f"/api/servers/{server_id}/availability/{overlapping_avail_id}",
                headers=_admin_headers(),
            )
            assert r.status_code == 409
        finally:
            await _cleanup_event(event_id)
            await _cleanup_server(server_id)

    async def test_servers_list_handles_null_worker_type_and_location_verified(self):
        server_id = await _create_test_server_direct()
        try:
            r = client.get("/api/servers", headers=_admin_headers(), params={"page_size": 100})
            assert r.status_code == 200
            data = r.json()
            server = next((s for s in data["items"] if s["id"] == server_id), None)
            assert server is not None
            assert server["worker_type"] == ""
            assert server["location_verified"] is False
        finally:
            await _cleanup_server(server_id)

    async def test_server_detail_handles_null_worker_type_and_location_verified(self):
        server_id = await _create_test_server_direct()
        try:
            r = client.get(f"/api/servers/{server_id}", headers=_admin_headers())
            assert r.status_code == 200
            data = r.json()
            assert data["worker_type"] == ""
            assert data["location"]["is_verified"] is False
        finally:
            await _cleanup_server(server_id)
