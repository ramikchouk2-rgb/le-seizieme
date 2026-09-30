import uuid
from datetime import datetime, timedelta

import pytest

from app.main import app
from app.core.database import get_pool
from app.services.selection_engine import generate_staff_recommendations

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"


def _admin_headers():
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_server_with_unique_skill(gender="MALE", years_experience=5, skill_level=5):
    """Create an isolated server owning a unique skill, so no other row can
    ever satisfy a requirement written against that role name."""
    server_id = uuid.uuid4()
    skill_name = f"Role {server_id.hex[:12]}"
    pool = await get_pool()
    async with pool.acquire() as conn:
        skill_id = await conn.fetchval(
            "INSERT INTO skills (name) VALUES ($1) RETURNING id",
            skill_name,
        )
        await conn.execute(
            """
            INSERT INTO servers (id, first_name, last_name, phone, email, gender, city_id, years_experience, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, (SELECT id FROM cities LIMIT 1), $7, TRUE)
            """,
            server_id,
            "Conflict",
            "Tester",
            "1234567890",
            f"conflict-{server_id}@test.com",
            gender,
            years_experience,
        )
        await conn.execute(
            """
            INSERT INTO server_skills (server_id, skill_id, level, years_experience)
            VALUES ($1, $2, $3, $4)
            """,
            server_id,
            skill_id,
            skill_level,
            2,
        )
    return str(server_id), skill_name


async def _create_event(start_hour=10, end_hour=12, status="STAFFING", day=15):
    event_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO events (id, name, client_name, city_id, address, start_datetime, end_datetime, guest_count, event_type, status)
            VALUES ($1, $2, $3, (SELECT id FROM cities LIMIT 1), $4, $5, $6, $7, $8, $9)
            """,
            event_id,
            f"Conflict Event {event_id}",
            "Test Client",
            "123 Test Street",
            datetime(2025, 3, day, start_hour, 0, 0),
            datetime(2025, 3, day, end_hour, 0, 0),
            10,
            "TEST",
            status,
        )
    return str(event_id)


async def _create_requirement(event_id, role_name, quantity=1):
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


async def _add_availability(server_id, start_hour=8, end_hour=20, day=15):
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
            datetime(2025, 3, day, start_hour, 0, 0),
            datetime(2025, 3, day, end_hour, 0, 0),
        )
    return str(avail_id)


async def _book_server_on_event(server_id, event_id, role_name, status="CONFIRMED"):
    """Insert a CONFIRMED/IN_PROGRESS assignment of server_id onto event_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_staff (event_id, server_id, role, assignment_status, confirmed_at)
            VALUES ($1, $2, $3, $4::assignment_status, CASE WHEN $5 THEN NOW() ELSE NULL END)
            """,
            event_id,
            server_id,
            role_name,
            status,
            status == "CONFIRMED",
        )


async def _create_urgent_offer(event_id, server_id, wave_number=1):
    offer_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO urgent_event_offers (id, event_id, server_id, wave_number, response_deadline, status)
            VALUES ($1, $2, $3, $4, NOW() + INTERVAL '15 minutes', 'PENDING')
            """,
            offer_id,
            event_id,
            server_id,
            wave_number,
        )
    return str(offer_id)


async def _cleanup(events, servers, skill_names):
    pool = await get_pool()
    async with pool.acquire() as conn:
        for event_id in events:
            await conn.execute("DELETE FROM urgent_event_offers WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_attendance WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_staff WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_requirements WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM events WHERE id = $1", event_id)
        for server_id in servers:
            await conn.execute("DELETE FROM server_availability WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM server_skills WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM event_staff WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM servers WHERE id = $1", server_id)
        for name in skill_names:
            await conn.execute("DELETE FROM skills WHERE name = $1", name)


def _candidate_ids(result, requirement_id):
    for req in result["requirements"]:
        if req["requirement"]["requirement_id"] == requirement_id:
            return {c["server_id"] for c in req["candidates"]}
    return set()


def _requirement_block(result, requirement_id):
    for req in result["requirements"]:
        if req["requirement"]["requirement_id"] == requirement_id:
            return req
    return None


class TestRecommendationConflictFiltering:
    async def test_server_without_overlapping_event_remains_eligible(self):
        server_id, skill = await _create_server_with_unique_skill()
        event_id = await _create_event(start_hour=10, end_hour=12)
        req_id = await _create_requirement(event_id, skill)
        await _add_availability(server_id)
        try:
            result = await generate_staff_recommendations(event_id)
            assert server_id in _candidate_ids(result, req_id)
        finally:
            await _cleanup([event_id], [server_id], [skill])

    async def test_overlapping_confirmed_event_is_excluded(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            result = await generate_staff_recommendations(target)
            assert server_id not in _candidate_ids(result, req_id)
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_overlapping_in_progress_event_is_excluded(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="IN_PROGRESS")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            result = await generate_staff_recommendations(target)
            assert server_id not in _candidate_ids(result, req_id)
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_non_overlapping_confirmed_event_remains_eligible(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=14, end_hour=16, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            result = await generate_staff_recommendations(target)
            assert server_id in _candidate_ids(result, req_id)
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_cancelled_event_does_not_block_eligibility(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CANCELLED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            result = await generate_staff_recommendations(target)
            assert server_id in _candidate_ids(result, req_id)
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_declined_assignment_does_not_block_eligibility(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO event_staff (event_id, server_id, role, assignment_status)
                VALUES ($1, $2, $3, 'DECLINED')
                """,
                blocking,
                server_id,
                skill,
            )
        try:
            result = await generate_staff_recommendations(target)
            assert server_id in _candidate_ids(result, req_id)
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_only_conflicting_candidates_are_excluded(self):
        free_id, free_skill = await _create_server_with_unique_skill()
        busy_id, busy_skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, free_skill)
        await _add_availability(free_id)
        await _add_availability(busy_id)
        # Give the busy server the same unique skill capability by pointing the
        # requirement at a skill both servers hold is not possible with unique
        # names, so instead verify per-server eligibility independently.
        req_free = req_id
        req_busy = await _create_requirement(target, busy_skill)
        await _book_server_on_event(busy_id, blocking, busy_skill)
        try:
            result = await generate_staff_recommendations(target)
            free_ids = _candidate_ids(result, req_free)
            busy_ids = _candidate_ids(result, req_busy)
            assert free_id in free_ids
            assert busy_id not in busy_ids
        finally:
            await _cleanup(
                [target, blocking], [free_id, busy_id], [free_skill, busy_skill]
            )

    async def test_requirement_reports_insufficient_staff_when_all_conflict(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, skill, quantity=1)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            result = await generate_staff_recommendations(target)
            block = _requirement_block(result, req_id)
            assert block is not None
            assert block["status"] == "INSUFFICIENT_STAFF"
            assert block["selected"] == []
            assert "Only 0/1" in block["message"]
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_conflicting_candidate_is_counted_as_excluded(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            result = await generate_staff_recommendations(target)
            assert result["total_excluded"] >= 1
            assert server_id not in _candidate_ids(result, req_id)
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_touching_but_not_overlapping_event_remains_eligible(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=12, end_hour=14, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            result = await generate_staff_recommendations(target)
            assert server_id in _candidate_ids(result, req_id)
        finally:
            await _cleanup([target, blocking], [server_id], [skill])


class TestConfirmationConflictBlocking:
    async def test_confirming_non_conflicting_server_succeeds(self):
        server_id, skill = await _create_server_with_unique_skill()
        event_id = await _create_event(start_hour=10, end_hour=12)
        req_id = await _create_requirement(event_id, skill)
        await _add_availability(server_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-staff",
                json={
                    "assignments": [
                        {"server_id": server_id, "requirement_id": req_id, "role": skill}
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Confirm failed: {r.text}"
        finally:
            await _cleanup([event_id], [server_id], [skill])

    async def test_confirming_overlapping_confirmed_event_is_blocked(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            r = client.post(
                f"/api/events/{target}/confirm-staff",
                json={
                    "assignments": [
                        {"server_id": server_id, "requirement_id": req_id, "role": skill}
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"
            assert "planning" in r.json()["detail"].lower()
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_confirming_overlapping_in_progress_event_is_blocked(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="IN_PROGRESS")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            r = client.post(
                f"/api/events/{target}/confirm-staff",
                json={
                    "assignments": [
                        {"server_id": server_id, "requirement_id": req_id, "role": skill}
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_non_overlapping_confirmation_succeeds(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=14, end_hour=16, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            r = client.post(
                f"/api/events/{target}/confirm-staff",
                json={
                    "assignments": [
                        {"server_id": server_id, "requirement_id": req_id, "role": skill}
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Confirm failed: {r.text}"
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_cancelled_historical_event_does_not_block_confirmation(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CANCELLED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            r = client.post(
                f"/api/events/{target}/confirm-staff",
                json={
                    "assignments": [
                        {"server_id": server_id, "requirement_id": req_id, "role": skill}
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Confirm failed: {r.text}"
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_declined_historical_assignment_does_not_block_confirmation(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO event_staff (event_id, server_id, role, assignment_status)
                VALUES ($1, $2, $3, 'DECLINED')
                """,
                blocking,
                server_id,
                skill,
            )
        try:
            r = client.post(
                f"/api/events/{target}/confirm-staff",
                json={
                    "assignments": [
                        {"server_id": server_id, "requirement_id": req_id, "role": skill}
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Confirm failed: {r.text}"
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_adding_staff_assignment_with_conflict_is_blocked(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        try:
            r = client.post(
                f"/api/events/{target}/staff",
                json={"server_id": server_id, "requirement_id": req_id, "role": skill},
                headers=_admin_headers(),
            )
            assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_adding_staff_assignment_without_conflict_succeeds(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12)
        req_id = await _create_requirement(target, skill)
        await _add_availability(server_id)
        try:
            r = client.post(
                f"/api/events/{target}/staff",
                json={"server_id": server_id, "requirement_id": req_id, "role": skill},
                headers=_admin_headers(),
            )
            assert r.status_code in (200, 201), f"Add failed: {r.text}"
        finally:
            await _cleanup([target], [server_id], [skill])


class TestUrgentOfferConflictBlocking:
    async def test_accepting_offer_with_overlapping_confirmed_event_is_rejected(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12, status="PLANNED")
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        offer_id = await _create_urgent_offer(target, server_id)
        try:
            r = client.post(
                f"/api/events/{target}/urgent-offers/{offer_id}/accept",
                headers=_admin_headers(),
            )
            assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
            assert "conflict" in r.json()["detail"].lower()
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_accepting_offer_with_overlapping_in_progress_event_is_rejected(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12, status="PLANNED")
        blocking = await _create_event(start_hour=11, end_hour=13, status="IN_PROGRESS")
        await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        offer_id = await _create_urgent_offer(target, server_id)
        try:
            r = client.post(
                f"/api/events/{target}/urgent-offers/{offer_id}/accept",
                headers=_admin_headers(),
            )
            assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        finally:
            await _cleanup([target, blocking], [server_id], [skill])

    async def test_accepting_offer_without_conflict_succeeds(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12, status="PLANNED")
        await _create_requirement(target, skill)
        await _add_availability(server_id)
        offer_id = await _create_urgent_offer(target, server_id)
        try:
            r = client.post(
                f"/api/events/{target}/urgent-offers/{offer_id}/accept",
                headers=_admin_headers(),
            )
            assert r.status_code == 200, f"Accept failed: {r.text}"
        finally:
            await _cleanup([target], [server_id], [skill])

    async def test_rejected_offer_remains_pending(self):
        server_id, skill = await _create_server_with_unique_skill()
        target = await _create_event(start_hour=10, end_hour=12, status="PLANNED")
        blocking = await _create_event(start_hour=11, end_hour=13, status="CONFIRMED")
        await _create_requirement(target, skill)
        await _add_availability(server_id)
        await _book_server_on_event(server_id, blocking, skill)
        offer_id = await _create_urgent_offer(target, server_id)
        try:
            r = client.post(
                f"/api/events/{target}/urgent-offers/{offer_id}/accept",
                headers=_admin_headers(),
            )
            assert r.status_code == 400
            pool = await get_pool()
            async with pool.acquire() as conn:
                status = await conn.fetchval(
                    "SELECT status FROM urgent_event_offers WHERE id = $1",
                    offer_id,
                )
            assert status == "PENDING"
        finally:
            await _cleanup([target, blocking], [server_id], [skill])
