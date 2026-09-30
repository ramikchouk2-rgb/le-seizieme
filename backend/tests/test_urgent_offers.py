"""Step 24C-D-3: urgent offer response contract and the event-detail envelope.

Two defects found during Step 24C-D-1/D-2:

  A. POST /events/{id}/urgent-offers/generate returned HTTP 500 whenever offers
     were actually generated. The engine returned the INSERT row keyed by `id`
     while UrgentOfferResponse declares `offer_id`, so FastAPI's response_model
     validation rejected the payload. The zero-offer path returned an empty list,
     which validated fine, so the bug only ever surfaced in production.

  B. app/models/events.py defined two classes named EventDetailResponse. Python
     rebound the module name to the second (the live envelope), so the first was
     unreachable; edits to it had no effect on the API.

These tests exercise the real HTTP/router response path, not the engine alone.
"""

import uuid
from datetime import datetime

import pytest

from app.core.database import get_pool
from app.main import app
from app.models.events import EventDetailEventResponse, EventDetailResponse

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"


def _admin_headers():
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_urgent_event(day, status="PLANNED", is_urgent=True):
    event_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO events (
                id, name, client_name, city_id, address, latitude, longitude,
                start_datetime, end_datetime, guest_count, event_type, status,
                is_urgent
            )
            VALUES (
                $1, $2, 'Urgent Client', (SELECT id FROM cities LIMIT 1),
                '1 Urgent Street', 40.4168, -3.7038,
                $3, $4, 80, 'URGENT', $5, $6
            )
            """,
            event_id,
            f"Urgent Event {event_id}",
            datetime(2025, 6, day, 9, 0, 0),
            datetime(2025, 6, day, 17, 0, 0),
            status,
            is_urgent,
        )
    return str(event_id)


async def _create_skill():
    skill_name = f"UrgentSkill-{uuid.uuid4().hex[:12]}"
    skill_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO skills (id, name) VALUES ($1, $2)", skill_id, skill_name)
    return skill_name, skill_id


async def _create_available_server(skill_id, day, years_experience=5):
    server_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO servers (
                id, first_name, last_name, email, phone, gender, city_id, years_experience
            )
            VALUES ($1, 'Urgent', 'Candidate', $2, '+21600000000', 'MALE',
                    (SELECT id FROM cities LIMIT 1), $3)
            """,
            server_id,
            f"{server_id}@example.org",
            years_experience,
        )
        await conn.execute(
            """
            INSERT INTO server_profile (
                server_id, worker_type, speed_score, punctuality_score,
                presentation_score, communication_score, teamwork_score,
                discipline_score, endurance_score
            )
            VALUES ($1, 'BALANCED', 7, 7, 7, 7, 7, 7, 7)
            """,
            server_id,
        )
        await conn.execute(
            "INSERT INTO server_skills (server_id, skill_id, level, years_experience) VALUES ($1, $2, 6, 2)",
            server_id,
            skill_id,
        )
        await conn.execute(
            """
            INSERT INTO server_availability (server_id, start_datetime, end_datetime, status)
            VALUES ($1, $2, $3, 'AVAILABLE')
            """,
            server_id,
            datetime(2025, 6, day, 0, 0, 0),
            datetime(2025, 6, day, 23, 59, 0),
        )
    return server_id


async def _create_requirement(event_id, role_name, quantity=1):
    req_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_requirements (
                id, event_id, role_name, quantity, minimum_skill_level, minimum_experience
            )
            VALUES ($1, $2, $3, $4, 1, 0)
            """,
            req_id,
            event_id,
            role_name,
            quantity,
        )
    return str(req_id)


async def _cleanup(events, servers, skill=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        for event_id in events:
            await conn.execute(
                "DELETE FROM urgent_event_offers WHERE event_id = $1", event_id
            )
            await conn.execute("DELETE FROM event_staff WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_requirements WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM events WHERE id = $1", event_id)
        for server_id in servers:
            await conn.execute(
                "DELETE FROM server_availability WHERE server_id = $1", server_id
            )
            await conn.execute("DELETE FROM server_skills WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM event_staff WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM servers WHERE id = $1", server_id)
        await conn.execute("DELETE FROM skills WHERE name = $1", skill) if skill else None


# ------------------------------------- A. urgent offer generation contract


class TestUrgentOfferGenerationResponse:
    async def test_generated_offers_pass_response_validation(self):
        """The regression: with at least one offer generated the endpoint 500'd.

        Exercised through the router so FastAPI's response_model filtering and
        validation run exactly as they do in production.
        """
        skill, skill_id = await _create_skill()
        server_id = await _create_available_server(skill_id, day=10)
        event_id = await _create_urgent_event(day=10)
        await _create_requirement(event_id, skill, quantity=1)
        try:
            r = client.post(
                f"/api/events/{event_id}/urgent-offers/generate", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            body = r.json()

            # Envelope fields survive.
            assert body["event_id"] == event_id
            assert body["status"] == "SUCCESS"
            assert body["wave_number"] == 1
            assert body["offers_created"] == 1

            # An offer really was generated.
            offers = body["offers"]
            assert len(offers) == 1, offers
            offer = offers[0]

            # Step 24C-D-3: the identifier is exposed as `offer_id`, never `id`.
            assert "offer_id" in offer
            assert "id" not in offer
            assert offer["server_id"] == str(server_id)
            assert offer["server_name"] == "Urgent Candidate"
            assert offer["role"] == skill
            assert offer["status"] == "PENDING"
            assert offer["wave_number"] == 1
            assert "created_at" in offer
            assert "expires_at" in offer
            assert offer["score"] is not None
        finally:
            await _cleanup([event_id], [server_id], skill)

    async def test_generated_offer_id_matches_the_persisted_row(self):
        """The emitted offer_id must be the real urgent_event_offers.id so the
        accept/decline/expire routes can act on it."""
        skill, skill_id = await _create_skill()
        server_id = await _create_available_server(skill_id, day=11)
        event_id = await _create_urgent_event(day=11)
        await _create_requirement(event_id, skill, quantity=1)
        try:
            r = client.post(
                f"/api/events/{event_id}/urgent-offers/generate", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            offer = r.json()["offers"][0]

            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, server_id FROM urgent_event_offers
                    WHERE event_id = $1 AND server_id = $2
                    """,
                    event_id,
                    server_id,
                )
            assert row is not None
            assert offer["offer_id"] == str(row["id"])
        finally:
            await _cleanup([event_id], [server_id], skill)

    async def test_generated_offer_id_is_usable_by_the_accept_route(self):
        """End-to-end proof that the identifier is a real, actionable offer id."""
        skill, skill_id = await _create_skill()
        server_id = await _create_available_server(skill_id, day=12)
        event_id = await _create_urgent_event(day=12)
        await _create_requirement(event_id, skill, quantity=1)
        try:
            headers = _admin_headers()
            generated = client.post(
                f"/api/events/{event_id}/urgent-offers/generate", headers=headers
            )
            assert generated.status_code == 200, generated.text
            offer_id = generated.json()["offers"][0]["offer_id"]

            accepted = client.post(
                f"/api/events/{event_id}/urgent-offers/{offer_id}/accept", headers=headers
            )
            assert accepted.status_code == 200, accepted.text
        finally:
            await _cleanup([event_id], [server_id], skill)

    async def test_zero_offer_generation_still_returns_a_valid_response(self):
        """STAFFING_COMPLETE returns no offers; the empty list must validate.

        An urgent event with no staffing requirement has nothing left to staff,
        which is the engine's zero-offer path. This is also why the original bug
        was invisible in existing tests: an empty offers list satisfies
        UrgentOfferResponse trivially, so only the non-empty path ever failed.
        """
        skill, _ = await _create_skill()
        event_id = await _create_urgent_event(day=13)
        try:
            r = client.post(
                f"/api/events/{event_id}/urgent-offers/generate", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["status"] == "STAFFING_COMPLETE"
            assert body["offers_created"] == 0
            assert body["offers"] == []
            assert body["requirements"] == []
            assert body["event_id"] == event_id
        finally:
            await _cleanup([event_id], [], skill)

    async def test_no_eligible_candidate_yields_zero_offers_and_still_validates(self):
        """A requirement nobody can satisfy must not 500 on an empty list."""
        skill, skill_id = await _create_skill()
        # Server available, but for a different skill than the requirement.
        server_id = await _create_available_server(skill_id, day=17)
        event_id = await _create_urgent_event(day=17)
        await _create_requirement(event_id, "RoleNobodyHas", quantity=1)
        try:
            r = client.post(
                f"/api/events/{event_id}/urgent-offers/generate", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["offers"] == []
            assert body["offers_created"] == 0
        finally:
            await _cleanup([event_id], [server_id], skill)

    async def test_non_urgent_event_is_still_rejected(self):
        """Pre-existing error behaviour must be preserved."""
        skill, skill_id = await _create_skill()
        event_id = await _create_urgent_event(day=14, is_urgent=False)
        try:
            r = client.post(
                f"/api/events/{event_id}/urgent-offers/generate", headers=_admin_headers()
            )
            assert r.status_code == 400
            assert r.json()["detail"] == "URGENT_EVENT_REQUIRED"
        finally:
            await _cleanup([event_id], [], skill)

    async def test_generated_offers_match_the_status_endpoint_contract(self):
        """generate and status must expose the same offer shape.

        UrgentStaffingPanel reads offer_id off both, so a divergence here would
        reintroduce the bug on the status side.
        """
        skill, skill_id = await _create_skill()
        server_id = await _create_available_server(skill_id, day=15)
        event_id = await _create_urgent_event(day=15)
        await _create_requirement(event_id, skill, quantity=1)
        try:
            headers = _admin_headers()
            generated = client.post(
                f"/api/events/{event_id}/urgent-offers/generate", headers=headers
            )
            assert generated.status_code == 200, generated.text
            status = client.get(
                f"/api/events/{event_id}/urgent-status", headers=headers
            )
            assert status.status_code == 200, status.text

            from app.models.urgent import UrgentOfferResponse

            expected = set(UrgentOfferResponse.model_fields)
            assert set(generated.json()["offers"][0]) == expected
            assert set(status.json()["offers"][0]) == expected
        finally:
            await _cleanup([event_id], [server_id], skill)


# ------------------------------------ B. event detail envelope model shape


class TestEventDetailEnvelope:
    def test_event_detail_response_resolves_to_the_live_envelope(self):
        """Step 24C-D-3: only one EventDetailResponse may exist, and it must be
        the envelope served by GET /events/{event_id}."""
        assert set(EventDetailResponse.model_fields) == {
            "event",
            "staffing",
            "requirements",
            "assignments",
            "transport",
        }

    def test_module_contains_exactly_one_event_detail_response(self):
        import inspect

        import app.models.events as events_module

        source = inspect.getsource(events_module)
        definitions = [
            line.strip()
            for line in source.splitlines()
            if line.startswith("class EventDetailResponse")
        ]
        assert definitions == ["class EventDetailResponse(BaseModel):"], definitions

    def test_event_detail_event_response_keeps_the_step_24c_d2_fields(self):
        fields = EventDetailEventResponse.model_fields
        for field in (
            "client_name",
            "event_type",
            "required_response_minutes",
            "notes",
            "city_id",
            "address",
            "latitude",
            "longitude",
        ):
            assert field in fields, f"EventDetailEventResponse lost '{field}'"

    async def test_event_detail_endpoint_still_returns_the_full_envelope(self):
        event_id = await _create_urgent_event(day=16)
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            body = r.json()

            assert set(body) == {
                "event",
                "staffing",
                "requirements",
                "assignments",
                "transport",
            }
            assert set(body["staffing"]) == {
                "requested",
                "selected",
                "missing",
                "percentage",
            }
            event = body["event"]
            assert event["client_name"] == "Urgent Client"
            assert event["event_type"] == "URGENT"
            assert event["city_id"] is not None
            assert event["address"] == "1 Urgent Street"
            assert event["latitude"] == pytest.approx(40.4168)
            assert event["longitude"] == pytest.approx(-3.7038)
        finally:
            await _cleanup([event_id], [], None)