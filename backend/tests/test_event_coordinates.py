"""Step 24C: event venue coordinates.

Covers:
  A. Event create with / without coordinates and range rejection
  B. Event update: coordinates, preserved address/city, no accidental nulling
  C. Event detail returning address, city_id and coordinates
  D. Selection: exact event coordinates used, server GPS never used as the
     venue, approximate state when the event has no coordinates
  E. Transport: destination is the venue, label carries address/city, final leg
  F. Privacy: server GPS is never exposed
"""

import uuid
from datetime import datetime
from typing import Optional

import pytest

from app.core.database import get_pool
from app.main import app
from app.services.selection_engine import generate_staff_recommendations
from app.utils.event_utils import load_event, resolve_event_location
from app.utils.selection_utils import haversine_km

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"

# A venue far from the technical fallback (Tunis Centre) so a fallback-based
# computation can never accidentally satisfy an exact-coordinate assertion.
VENUE_LAT = 40.4168
VENUE_LON = -3.7038


def _admin_headers():
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_event(
    latitude=None,
    longitude=None,
    address="123 Coordinate Street",
    status="PLANNED",
    day=20,
    client_name="Coordinate Client",
    event_type="TEST",
    notes=None,
    required_response_minutes=None,
    is_urgent=False,
):
    event_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO events (
                id, name, client_name, city_id, address, latitude, longitude,
                start_datetime, end_datetime, guest_count, event_type, status,
                notes, required_response_minutes, is_urgent
            )
            VALUES (
                $1, $2, $3, (SELECT id FROM cities LIMIT 1), $4, $5, $6,
                $7, $8, 50, $9, $10, $11, $12, $13
            )
            """,
            event_id,
            f"Coordinate Event {event_id}",
            client_name,
            address,
            latitude,
            longitude,
            datetime(2025, 5, day, 10, 0, 0),
            datetime(2025, 5, day, 14, 0, 0),
            event_type,
            status,
            notes,
            required_response_minutes,
            is_urgent,
        )
    return str(event_id)


async def _cleanup(events, servers=(), locations=()):
    pool = await get_pool()
    async with pool.acquire() as conn:
        for event_id in events:
            await conn.execute("DELETE FROM transport_passengers WHERE transport_group_id IN (SELECT id FROM transport_groups WHERE event_id = $1)", event_id)
            await conn.execute("DELETE FROM transport_groups WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_staff WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_requirements WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM events WHERE id = $1", event_id)
        for server_id in locations:
            await conn.execute("DELETE FROM server_locations WHERE server_id = $1", server_id)
        for server_id in servers:
            await conn.execute("DELETE FROM server_availability WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM server_skills WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM event_staff WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM servers WHERE id = $1", server_id)


async def _create_server_with_location(
    latitude, longitude, skill_level=5, years_experience=5, day=20
):
    """A server holding a unique skill plus a verified personal GPS position."""
    server_id = uuid.uuid4()
    skill_name = f"CoordRole {server_id.hex[:12]}"
    pool = await get_pool()
    async with pool.acquire() as conn:
        skill_id = await conn.fetchval(
            "INSERT INTO skills (name) VALUES ($1) RETURNING id", skill_name
        )
        await conn.execute(
            """
            INSERT INTO servers (id, first_name, last_name, phone, email, gender, city_id, years_experience, is_active)
            VALUES ($1, 'Coord', 'Tester', '1234567891', $2, 'MALE', (SELECT id FROM cities LIMIT 1), $3, TRUE)
            """,
            server_id,
            f"coord-{server_id}@test.com",
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
            "INSERT INTO server_skills (server_id, skill_id, level, years_experience) VALUES ($1, $2, $3, 2)",
            server_id,
            skill_id,
            skill_level,
        )
        await conn.execute(
            """
            INSERT INTO server_locations (server_id, city_id, latitude, longitude, is_verified, is_current)
            VALUES ($1, (SELECT id FROM cities LIMIT 1), $2, $3, TRUE, TRUE)
            """,
            server_id,
            latitude,
            longitude,
        )
        await conn.execute(
            """
            INSERT INTO server_availability (server_id, start_datetime, end_datetime, status)
            VALUES ($1, $2, $3, 'AVAILABLE')
            """,
            server_id,
            datetime(2025, 5, day, 6, 0, 0),
            datetime(2025, 5, day, 22, 0, 0),
        )
    return str(server_id), skill_name, str(skill_id)


async def _create_requirement(event_id, role_name, skill_id, quantity=1):
    req_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_requirements (id, event_id, role_name, quantity, minimum_skill_level, minimum_experience)
            VALUES ($1, $2, $3, $4, 1, 0)
            """,
            req_id,
            event_id,
            role_name,
            quantity,
        )
    return str(req_id)


def _event_payload(city_id, **overrides):
    payload = {
        "name": "Coordinate API Event",
        "client_name": "API Client",
        "city_id": city_id,
        "address": "9 Venue Road, Central",
        "start_datetime": "2025-05-20T10:00:00",
        "end_datetime": "2025-05-20T14:00:00",
        "guest_count": 60,
        "event_type": "WEDDING",
    }
    payload.update(overrides)
    return payload


async def _first_city_id():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return str(await conn.fetchval("SELECT id FROM cities ORDER BY name LIMIT 1"))


# ---------------------------------------------------------------- A. create


class TestEventCreateCoordinates:
    async def test_create_with_coordinates_persists_them(self):
        city_id = await _first_city_id()
        r = client.post(
            "/api/events",
            json=_event_payload(city_id, latitude=VENUE_LAT, longitude=VENUE_LON),
            headers=_admin_headers(),
        )
        assert r.status_code == 200, r.text
        event_id = r.json()["id"]
        try:
            assert r.json()["latitude"] == pytest.approx(VENUE_LAT)
            assert r.json()["longitude"] == pytest.approx(VENUE_LON)
            pool = await get_pool()
            async with pool.acquire() as conn:
                lat, lon = await conn.fetchrow(
                    "SELECT latitude, longitude FROM events WHERE id = $1", event_id
                )
            assert float(lat) == pytest.approx(VENUE_LAT)
            assert float(lon) == pytest.approx(VENUE_LON)
        finally:
            await _cleanup([event_id])

    async def test_create_without_coordinates_is_accepted(self):
        city_id = await _first_city_id()
        r = client.post("/api/events", json=_event_payload(city_id), headers=_admin_headers())
        assert r.status_code == 200, r.text
        event_id = r.json()["id"]
        try:
            assert r.json()["latitude"] is None
            assert r.json()["longitude"] is None
        finally:
            await _cleanup([event_id])

    async def test_create_with_null_coordinates_is_accepted(self):
        city_id = await _first_city_id()
        r = client.post(
            "/api/events",
            json=_event_payload(city_id, latitude=None, longitude=None),
            headers=_admin_headers(),
        )
        assert r.status_code == 200, r.text
        event_id = r.json()["id"]
        try:
            assert r.json()["latitude"] is None
            assert r.json()["longitude"] is None
        finally:
            await _cleanup([event_id])

    @pytest.mark.parametrize("bad_lat", [-90.1, 90.1, 1000])
    async def test_create_rejects_invalid_latitude(self, bad_lat):
        city_id = await _first_city_id()
        r = client.post(
            "/api/events",
            json=_event_payload(city_id, latitude=bad_lat, longitude=VENUE_LON),
            headers=_admin_headers(),
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    @pytest.mark.parametrize("bad_lon", [-180.1, 180.1, 1000])
    async def test_create_rejects_invalid_longitude(self, bad_lon):
        city_id = await _first_city_id()
        r = client.post(
            "/api/events",
            json=_event_payload(city_id, latitude=VENUE_LAT, longitude=bad_lon),
            headers=_admin_headers(),
        )
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    @pytest.mark.parametrize("lat,lon", [(-90, -180), (90, 180), (0, 0)])
    async def test_create_accepts_boundary_coordinates(self, lat, lon):
        city_id = await _first_city_id()
        r = client.post(
            "/api/events",
            json=_event_payload(city_id, latitude=lat, longitude=lon),
            headers=_admin_headers(),
        )
        assert r.status_code == 200, r.text
        event_id = r.json()["id"]
        try:
            assert r.json()["latitude"] == pytest.approx(lat)
            assert r.json()["longitude"] == pytest.approx(lon)
        finally:
            await _cleanup([event_id])

    async def test_invalid_coordinates_are_not_silently_clamped(self):
        city_id = await _first_city_id()
        r = client.post(
            "/api/events",
            json=_event_payload(city_id, latitude=91, longitude=0),
            headers=_admin_headers(),
        )
        assert r.status_code == 422
        pool = await get_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT count(*) FROM events WHERE name = $1", "Coordinate API Event"
            )
        assert count == 0


# ---------------------------------------------------------------- B. update


class TestEventUpdateCoordinates:
    async def test_update_coordinates(self):
        event_id = await _create_event()
        try:
            r = client.patch(
                f"/api/events/{event_id}",
                json={"latitude": VENUE_LAT, "longitude": VENUE_LON},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            assert r.json()["latitude"] == pytest.approx(VENUE_LAT)
            assert r.json()["longitude"] == pytest.approx(VENUE_LON)
        finally:
            await _cleanup([event_id])

    async def test_update_preserves_address_and_city_id(self):
        original = "17 Keep Street"
        event_id = await _create_event(address=original)
        try:
            before = client.get(f"/api/events/{event_id}", headers=_admin_headers()).json()
            r = client.patch(
                f"/api/events/{event_id}",
                json={"latitude": VENUE_LAT, "longitude": VENUE_LON},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            assert r.json()["address"] == original
            assert r.json()["city_id"] == before["event"]["city_id"]

            after = client.get(f"/api/events/{event_id}", headers=_admin_headers()).json()
            assert after["event"]["address"] == original
            assert after["event"]["city_id"] == before["event"]["city_id"]
        finally:
            await _cleanup([event_id])

    async def test_partial_update_does_not_wipe_coordinates(self):
        event_id = await _create_event(latitude=VENUE_LAT, longitude=VENUE_LON)
        try:
            r = client.patch(
                f"/api/events/{event_id}",
                json={"address": "42 New Address"},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            assert r.json()["latitude"] == pytest.approx(VENUE_LAT)
            assert r.json()["longitude"] == pytest.approx(VENUE_LON)
            assert r.json()["address"] == "42 New Address"
        finally:
            await _cleanup([event_id])

    async def test_partial_update_does_not_wipe_address_or_city(self):
        event_id = await _create_event(address="77 Original Street")
        try:
            r = client.patch(
                f"/api/events/{event_id}",
                json={"latitude": VENUE_LAT, "longitude": VENUE_LON},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            detail = client.get(f"/api/events/{event_id}", headers=_admin_headers()).json()
            assert detail["event"]["address"] == "77 Original Street"
            assert detail["event"]["city_id"] is not None
        finally:
            await _cleanup([event_id])

    async def test_update_rejects_invalid_coordinates(self):
        event_id = await _create_event()
        try:
            r = client.patch(
                f"/api/events/{event_id}",
                json={"latitude": 95},
                headers=_admin_headers(),
            )
            assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        finally:
            await _cleanup([event_id])

    async def test_coordinates_can_be_cleared_explicitly(self):
        event_id = await _create_event(latitude=VENUE_LAT, longitude=VENUE_LON)
        try:
            r = client.patch(
                f"/api/events/{event_id}",
                json={"latitude": None, "longitude": None},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            assert r.json()["latitude"] is None
            assert r.json()["longitude"] is None
        finally:
            await _cleanup([event_id])

    async def test_unknown_event_id_returns_404(self):
        r = client.patch(
            "/api/events/00000000-0000-0000-0000-000000000000",
            json={"latitude": 1.0, "longitude": 1.0},
            headers=_admin_headers(),
        )
        assert r.status_code == 404


# ---------------------------------------------------------------- C. detail


class TestEventDetailLocation:
    async def test_detail_returns_address_city_and_coordinates(self):
        event_id = await _create_event(
            latitude=VENUE_LAT,
            longitude=VENUE_LON,
            address="31 Detail Avenue",
        )
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            assert event["address"] == "31 Detail Avenue"
            assert event["city_id"] is not None
            assert event["latitude"] == pytest.approx(VENUE_LAT)
            assert event["longitude"] == pytest.approx(VENUE_LON)
        finally:
            await _cleanup([event_id])

    async def test_detail_returns_null_coordinates_when_unset(self):
        event_id = await _create_event(address="32 Detail Avenue")
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            assert event["latitude"] is None
            assert event["longitude"] is None
            assert event["address"] == "32 Detail Avenue"
        finally:
            await _cleanup([event_id])


# --------------------------------------------- C2. Step 24C-D-2 detail contract


class TestEventDetailResponseContract:
    """GET /api/events/{id} must expose the event fields the events table holds.

    Step 24C-D-2: get_event_staff_summary() already selected and emitted
    client_name, event_type, required_response_minutes and notes, but
    EventDetailEventResponse did not declare them, so FastAPI's response_model
    filtering silently dropped all four. These tests pin the corrected contract
    and guard the fields the previous fix must not have disturbed.
    """

    async def test_detail_returns_the_four_previously_missing_fields(self):
        event_id = await _create_event(
            latitude=VENUE_LAT,
            longitude=VENUE_LON,
            address="33 Contract Avenue",
            client_name="Maison Des JARDins",
            event_type="MARIAGE",
            notes="Poolside service, load-in from the service entrance.",
            required_response_minutes=45,
        )
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            assert event["client_name"] == "Maison Des JARDins"
            assert event["event_type"] == "MARIAGE"
            assert event["notes"] == "Poolside service, load-in from the service entrance."
            assert event["required_response_minutes"] == 45
        finally:
            await _cleanup([event_id])

    async def test_detail_keeps_nullable_fields_null_when_unset(self):
        event_id = await _create_event(address="34 Contract Avenue")
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            # The keys must be present even when the columns are NULL, so the
            # frontend can rely on the shape rather than probing for it.
            assert "notes" in event
            assert "required_response_minutes" in event
            assert event["notes"] is None
            assert event["required_response_minutes"] is None
        finally:
            await _cleanup([event_id])

    async def test_detail_preserves_the_pre_existing_fields(self):
        event_id = await _create_event(
            latitude=VENUE_LAT,
            longitude=VENUE_LON,
            address="35 Regression Avenue",
            status="CONFIRMED",
            day=24,
        )
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            body = r.json()
            event = body["event"]
            # Fields Step 24C-B introduced must survive the contract change.
            assert event["city_id"] is not None
            assert event["address"] == "35 Regression Avenue"
            assert event["latitude"] == pytest.approx(VENUE_LAT)
            assert event["longitude"] == pytest.approx(VENUE_LON)
            # Fields that predate both steps must survive too.
            assert event["id"] == event_id
            assert event["name"].startswith("Coordinate Event")
            assert event["guest_count"] == 50
            assert event["status"] == "CONFIRMED"
            assert event["priority"]
            assert event["alcohol_service"] is False
            assert event["food_products_count"] == 0
            assert event["urgent"] is False
            # And the surrounding envelope is untouched.
            assert set(body) == {"event", "staffing", "requirements", "assignments", "transport"}
            assert set(body["staffing"]) == {"requested", "selected", "missing", "percentage"}
        finally:
            await _cleanup([event_id])

    async def test_event_detail_event_response_declares_the_four_fields(self):
        # Structural guard: a future edit that removes one of the four fields
        # from the response model must fail here, not silently shrink the API.
        from app.models.events import EventDetailEventResponse

        fields = EventDetailEventResponse.model_fields
        for field in ("client_name", "event_type", "required_response_minutes", "notes"):
            assert field in fields, f"EventDetailEventResponse lost '{field}'"
        # client_name and event_type are NOT NULL in the events table, so they
        # must stay required; the other two are genuinely nullable.
        assert fields["client_name"].is_required()
        assert fields["event_type"].is_required()
        assert not fields["required_response_minutes"].is_required()
        assert not fields["notes"].is_required()
        assert fields["required_response_minutes"].annotation == Optional[int]
        assert fields["notes"].annotation == Optional[str]


# -------------------------------------------------------------- D. selection


class TestSelectionUsesVenueCoordinates:
    def test_resolver_uses_event_columns(self):
        lat, lon, exact = resolve_event_location({"latitude": VENUE_LAT, "longitude": VENUE_LON})
        assert (lat, lon, exact) == (VENUE_LAT, VENUE_LON, True)

    def test_resolver_falls_back_and_flags_approximate(self):
        lat, lon, exact = resolve_event_location({"latitude": None, "longitude": None})
        assert exact is False
        assert lat == 36.8065 and lon == 10.1815

    def test_resolver_ignores_partial_coordinates(self):
        lat, lon, exact = resolve_event_location({"latitude": VENUE_LAT, "longitude": None})
        assert exact is False

    def test_haversine_is_canonical_in_selection_utils(self):
        from app.services import selection_engine

        assert selection_engine.haversine_km is haversine_km
        assert haversine_km(0, 0, 0, 1) == pytest.approx(111.2, abs=0.5)

    async def test_exact_event_coordinates_are_used_for_distance(self):
        # Server sits ~1 km from the venue and ~1500 km from the technical
        # fallback, so the reported distance proves which reference was used.
        server_id, skill, skill_id = await _create_server_with_location(
            VENUE_LAT + 0.005, VENUE_LON
        )
        event_id = await _create_event(latitude=VENUE_LAT, longitude=VENUE_LON, day=20)
        req_id = await _create_requirement(event_id, skill, skill_id)
        try:
            result = await generate_staff_recommendations(event_id)
            assert result["event"]["has_exact_location"] is True
            candidate = next(
                c
                for r in result["requirements"]
                for c in r["candidates"]
                if c["server_id"] == server_id
            )
            expected = haversine_km(VENUE_LAT, VENUE_LON, VENUE_LAT + 0.005, VENUE_LON)
            assert candidate["distance_km"] == pytest.approx(expected, abs=0.5)
            assert candidate["distance_km"] < 10
        finally:
            await _cleanup([event_id], [server_id], [server_id])
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM skills WHERE name = $1", skill)

    async def test_server_location_is_never_used_as_event_location(self):
        # The event has NO coordinates. The only server in the system holds a
        # verified personal GPS position in a totally different place. The
        # scoring must not borrow it as the venue.
        server_id, skill, skill_id = await _create_server_with_location(
            48.8566, 2.3522, day=21
        )
        event_id = await _create_event(day=21)
        req_id = await _create_requirement(event_id, skill, skill_id)
        try:
            result = await generate_staff_recommendations(event_id)
            assert result["event"]["has_exact_location"] is False
            candidate = next(
                c
                for r in result["requirements"]
                for c in r["candidates"]
                if c["server_id"] == server_id
            )
            # Neutralized: no distance is asserted for an unknown venue.
            assert candidate["distance_km"] is None
            assert not any("km from event" in reason for reason in candidate["reasons"])
        finally:
            await _cleanup([event_id], [server_id], [server_id])
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM skills WHERE name = $1", skill)

    async def test_load_event_does_not_read_server_locations(self):
        event_id = await _create_event(latitude=VENUE_LAT, longitude=VENUE_LON)
        try:
            event = await load_event(event_id)
            assert event["has_exact_location"] is True
            assert float(event["latitude"]) == pytest.approx(VENUE_LAT)
            assert "event_latitude" not in event
            assert "event_longitude" not in event
        finally:
            await _cleanup([event_id])


# -------------------------------------------------------------- E. transport


class TestTransportDestinationIsVenue:
    async def _confirm_transport(self, event_id, driver_id, passenger_id):
        return client.post(
            f"/api/events/{event_id}/confirm-transport",
            json={
                "groups": [
                    {
                        "driver_server_id": driver_id,
                        "passengers": [
                            {"server_id": passenger_id, "pickup_order": 1}
                        ],
                    }
                ]
            },
            headers=_admin_headers(),
        )

    async def _book_staff(self, event_id, server_id, role="Guest"):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO event_staff (event_id, server_id, role, assignment_status, confirmed_at)
                VALUES ($1, $2, $3, 'CONFIRMED', NOW())
                """,
                event_id,
                server_id,
                role,
            )

    async def _create_vehicle(self, owner_id):
        vehicle_id = uuid.uuid4()
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO vehicles (id, owner_server_id, vehicle_type, brand, model, seats_total, can_transport_coworkers, is_active)
                VALUES ($1, $2, 'CAR', 'Venue', 'Test', 4, TRUE, TRUE)
                """,
                vehicle_id,
                owner_id,
            )
        return str(vehicle_id)

    async def test_destination_equals_event_coordinates_and_final_leg_included(self):
        driver_id, _, _ = await _create_server_with_location(VENUE_LAT, VENUE_LON + 0.01, day=20)
        passenger_id, _, _ = await _create_server_with_location(VENUE_LAT + 0.02, VENUE_LON + 0.01, day=20)
        event_id = await _create_event(
            latitude=VENUE_LAT,
            longitude=VENUE_LON,
            address="55 Venue Street",
            status="CONFIRMED",
            day=20,
        )
        vehicle_id = await self._create_vehicle(driver_id)
        try:
            await self._book_staff(event_id, driver_id)
            await self._book_staff(event_id, passenger_id)
            r = await self._confirm_transport(event_id, driver_id, passenger_id)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["groups"][0]["has_exact_location"] is True

            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT destination_latitude, destination_longitude, destination_label,
                           estimated_distance_km
                    FROM transport_groups WHERE event_id = $1
                    """,
                    event_id,
                )
                city_name = await conn.fetchval(
                    "SELECT c.name FROM events e JOIN cities c ON c.id = e.city_id WHERE e.id = $1",
                    event_id,
                )
            assert float(row["destination_latitude"]) == pytest.approx(VENUE_LAT)
            assert float(row["destination_longitude"]) == pytest.approx(VENUE_LON)
            assert row["destination_label"] == f"55 Venue Street, {city_name}"
            assert "position approximative" not in row["destination_label"]

            # The destination is the venue, so the route is strictly longer than
            # the driver -> passenger leg alone.
            driver_to_passenger = haversine_km(
                VENUE_LAT, VENUE_LON + 0.01, VENUE_LAT + 0.02, VENUE_LON + 0.01
            )
            final_leg = haversine_km(VENUE_LAT + 0.02, VENUE_LON + 0.01, VENUE_LAT, VENUE_LON)
            assert float(row["estimated_distance_km"]) == pytest.approx(
                driver_to_passenger + final_leg, abs=0.2
            )
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [driver_id, passenger_id])
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM vehicles WHERE id = $1", vehicle_id)

    async def test_destination_is_approximate_when_event_has_no_coordinates(self):
        driver_id, _, _ = await _create_server_with_location(VENUE_LAT, VENUE_LON + 0.01, day=22)
        passenger_id, _, _ = await _create_server_with_location(VENUE_LAT + 0.02, VENUE_LON + 0.01, day=22)
        event_id = await _create_event(
            address="56 Venue Street",
            status="CONFIRMED",
            day=22,
        )
        vehicle_id = await self._create_vehicle(driver_id)
        try:
            await self._book_staff(event_id, driver_id)
            await self._book_staff(event_id, passenger_id)
            r = await self._confirm_transport(event_id, driver_id, passenger_id)
            assert r.status_code == 200, r.text
            assert r.json()["groups"][0]["has_exact_location"] is False

            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT destination_latitude, destination_longitude, destination_label
                    FROM transport_groups WHERE event_id = $1
                    """,
                    event_id,
                )
            # Never the driver's own position, and the approximation is stated.
            assert float(row["destination_latitude"]) != pytest.approx(VENUE_LAT)
            assert "56 Venue Street" in row["destination_label"]
            assert "position approximative" in row["destination_label"]
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [driver_id, passenger_id])
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM vehicles WHERE id = $1", vehicle_id)


# ----------------------------------------------------------------- F. privacy

# Every field name that would indicate a raw geographic fix crossing the API
# boundary. `server_locations` is the only source of a server's personal GPS;
# none of these may ever be projected into a response model or payload.
SERVER_GPS_FIELDS = frozenset(
    {
        "latitude",
        "longitude",
        "current_latitude",
        "current_longitude",
        "pickup_latitude",
        "pickup_longitude",
        "departure_latitude",
        "departure_longitude",
        "destination_latitude",
        "destination_longitude",
    }
)

# The single legitimate exception: the event venue on the event-detail payload.
# An event's coordinates describe a place, not a person, and Step 24C-B made
# them first-class event data. They are asserted to be PRESENT here, so the
# allowlist cannot be used to quietly delete them.
ALLOWED_VENUE_PATHS = frozenset({"$.event.latitude", "$.event.longitude"})

# A server's personal GPS fixture, deliberately far from VENUE_LAT/VENUE_LON so
# the two value sets can never be confused.
SERVER_LAT = 48.8566
SERVER_LON = 2.3522
SERVER_GPS_VALUES = ("48.8566", "2.3522")

# Endpoints whose response models may contain server, driver or passenger data.
# Read from the live routing table at test time, so a newly added endpoint is
# not silently excluded from the static check below.
SERVER_DATA_ENDPOINTS = (
    ("/api/servers", "GET"),
    ("/api/servers/stats", "GET"),
    ("/api/servers/{server_id}", "GET"),
    ("/api/servers/{server_id}/points", "GET"),
    ("/api/servers/{server_id}/availability", "GET"),
    ("/api/servers/{server_id}/availability/check", "GET"),
    ("/api/events/{event_id}", "GET"),
    ("/api/events/{event_id}/operations", "GET"),
    ("/api/events/{event_id}/eligible-staff", "GET"),
    ("/api/events/{event_id}/report", "GET"),
    ("/api/events/{event_id}/attendance", "GET"),
    ("/api/events/{event_id}/urgent-status", "GET"),
    ("/api/events/{event_id}/generate-staff", "POST"),
    ("/api/events/{event_id}/recommend-transport", "POST"),
    ("/api/events/{event_id}/confirm-transport", "POST"),
    ("/api/events/{event_id}/urgent-offers/generate", "POST"),
)


def _walk_payload(node, path="$"):
    """Yield every ``(path, dict)`` pair in a decoded JSON payload."""
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from _walk_payload(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_payload(value, f"{path}[{index}]")


def _walk_model(model, path="$"):
    """Yield every ``(path, field_name)`` pair declared by a Pydantic model."""
    fields = getattr(model, "model_fields", None)
    if not fields:
        return
    for name, info in fields.items():
        yield f"{path}.{name}", name
        annotation = getattr(info, "annotation", None)
        yield from _walk_model(annotation, f"{path}.{name}")
        for extra in getattr(info, "metadata", []) or []:
            yield from _walk_model(extra, f"{path}.{name}")


def _assert_no_server_gps(body, label):
    """Assert a decoded payload carries no raw server GPS.

    Structural first: any GPS-shaped key is rejected unless it is the event
    venue, which is the only position in the product that is not a person.
    """
    for path, node in _walk_payload(body):
        for key in node:
            if key in SERVER_GPS_FIELDS:
                where = f"{path}.{key}"
                assert where in ALLOWED_VENUE_PATHS, (
                    f"{label}: raw GPS field '{key}' exposed at {where}"
                )
    # Value-level: the fixture's own coordinates must appear nowhere at all,
    # which also catches a leak expressed as a bare number or a nested string.
    serialized = str(body)
    for value in SERVER_GPS_VALUES:
        assert value not in serialized, f"{label}: server GPS value {value} leaked"


def _response_model_for(path, method):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return getattr(route, "response_model", None)
    return None


class TestServerGpsNotExposed:
    async def test_server_endpoints_never_return_raw_gps(self):
        server_id, _, _ = await _create_server_with_location(SERVER_LAT, SERVER_LON)
        headers = _admin_headers()
        try:
            for url in (
                "/api/servers?location_verified=true",
                f"/api/servers/{server_id}",
            ):
                r = client.get(url, headers=headers)
                assert r.status_code == 200, f"{url} -> {r.status_code}"
                _assert_no_server_gps(r.json(), url)
                serialized = str(r.json())
                for banned in SERVER_GPS_FIELDS:
                    assert banned not in serialized, f"{banned} leaked by {url}"
        finally:
            await _cleanup([], [server_id], [server_id])

    async def test_staff_recommendation_never_returns_raw_gps(self):
        server_id, skill, skill_id = await _create_server_with_location(SERVER_LAT, SERVER_LON)
        event_id = await _create_event(latitude=VENUE_LAT, longitude=VENUE_LON, day=23)
        req_id = await _create_requirement(event_id, skill, skill_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/generate-staff", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            body = r.json()
            _assert_no_server_gps(body, "generate-staff")
            serialized = str(body)
            for banned in ("current_latitude", "current_longitude", "48.8566", "2.3522"):
                assert banned not in serialized, f"{banned} leaked by staff recommendations"
        finally:
            await _cleanup([event_id], [server_id], [server_id])
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM skills WHERE name = $1", skill)


class TestServerGpsNeverCrossesTheApiBoundary:
    """Step 24C-D-1: broaden the privacy net beyond the two original endpoints.

    The original suite proved /api/servers and generate-staff were clean. Event
    detail, operations, eligible-staff, urgent-status, availability and both
    transport endpoints all surface server, driver or passenger records and were
    previously unchecked.
    """

    async def _seed_full_event(self, day):
        """Event + server + requirement + assignment + vehicle + transport."""
        driver_id, driver_skill, driver_skill_id = await _create_server_with_location(
            SERVER_LAT, SERVER_LON, day=day
        )
        passenger_id, _, _ = await _create_server_with_location(
            SERVER_LAT + 0.02, SERVER_LON + 0.01, day=day
        )
        event_id = await _create_event(
            latitude=VENUE_LAT,
            longitude=VENUE_LON,
            address="57 Privacy Avenue",
            status="CONFIRMED",
            day=day,
            is_urgent=True,
        )
        await _create_requirement(event_id, driver_skill, driver_skill_id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO event_staff (event_id, server_id, role, assignment_status, confirmed_at)
                VALUES ($1, $2, 'Driver', 'CONFIRMED', NOW())
                """,
                event_id,
                driver_id,
            )
            await conn.execute(
                """
                INSERT INTO event_staff (event_id, server_id, role, assignment_status, confirmed_at)
                VALUES ($1, $2, 'Guest', 'CONFIRMED', NOW())
                """,
                event_id,
                passenger_id,
            )
            vehicle_id = await conn.fetchval(
                """
                INSERT INTO vehicles (owner_server_id, vehicle_type, brand, model, seats_total, can_transport_coworkers, is_active)
                VALUES ($1, 'CAR', 'Privacy', 'Test', 4, TRUE, TRUE)
                RETURNING id
                """,
                driver_id,
            )
        return event_id, driver_id, passenger_id, vehicle_id, driver_skill

    async def _teardown(self, event_id, driver_id, passenger_id, vehicle_id, skill):
        await _cleanup([event_id], [driver_id, passenger_id], [driver_id, passenger_id])
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM vehicles WHERE id = $1", vehicle_id)
            await conn.execute("DELETE FROM skills WHERE name = $1", skill)

    async def test_event_scoped_endpoints_never_return_raw_server_gps(self):
        event_id, driver_id, passenger_id, vehicle_id, skill = await self._seed_full_event(day=25)
        headers = _admin_headers()
        try:
            # Confirm transport first so the transport sections are populated.
            confirm = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": driver_id,
                            "passengers": [{"server_id": passenger_id, "pickup_order": 1}],
                        }
                    ]
                },
                headers=headers,
            )
            assert confirm.status_code == 200, confirm.text

            probes = [
                ("GET", f"/api/events/{event_id}", None),
                ("GET", f"/api/events/{event_id}/operations", None),
                ("GET", f"/api/events/{event_id}/eligible-staff", None),
                ("GET", f"/api/events/{event_id}/urgent-status", None),
                ("GET", f"/api/events/{event_id}/attendance", None),
                ("GET", f"/api/servers/{driver_id}", None),
                ("GET", f"/api/servers/{driver_id}/availability", None),
                ("GET", f"/api/servers/{driver_id}/availability/check?event_id={event_id}", None),
                ("GET", f"/api/servers/{driver_id}/points", None),
                ("GET", "/api/servers?location_verified=true", None),
                ("POST", f"/api/events/{event_id}/generate-staff", None),
                ("POST", f"/api/events/{event_id}/recommend-transport", None),
            ]
            for method, url, _ in probes:
                if method == "GET":
                    r = client.get(url, headers=headers)
                else:
                    r = client.post(url, headers=headers)
                assert r.status_code == 200, f"{method} {url} -> {r.status_code}: {r.text}"
                _assert_no_server_gps(r.json(), f"{method} {url}")
        finally:
            await self._teardown(event_id, driver_id, passenger_id, vehicle_id, skill)

    async def test_transport_endpoints_never_return_raw_server_gps(self):
        event_id, driver_id, passenger_id, vehicle_id, skill = await self._seed_full_event(day=26)
        headers = _admin_headers()
        try:
            for url, body in (
                (f"/api/events/{event_id}/recommend-transport", None),
                (
                    f"/api/events/{event_id}/confirm-transport",
                    {
                        "groups": [
                            {
                                "driver_server_id": driver_id,
                                "passengers": [{"server_id": passenger_id, "pickup_order": 1}],
                            }
                        ]
                    },
                ),
            ):
                r = client.post(url, json=body, headers=headers)
                assert r.status_code == 200, f"{url} -> {r.status_code}: {r.text}"
                _assert_no_server_gps(r.json(), url)
        finally:
            await self._teardown(event_id, driver_id, passenger_id, vehicle_id, skill)

    async def test_event_detail_exposes_venue_coordinates_but_no_server_coordinates(self):
        """The two kinds of coordinates must stay distinguishable.

        The event venue is legitimate event data and must be present. The
        server's own position must be absent even though the payload also
        contains assigned servers and a confirmed transport plan.
        """
        event_id, driver_id, passenger_id, vehicle_id, skill = await self._seed_full_event(day=27)
        try:
            confirm = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": driver_id,
                            "passengers": [{"server_id": passenger_id, "pickup_order": 1}],
                        }
                    ]
                },
                headers=_admin_headers(),
            )
            assert confirm.status_code == 200, confirm.text

            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            body = r.json()

            # Venue present and correct.
            assert body["event"]["latitude"] == pytest.approx(VENUE_LAT)
            assert body["event"]["longitude"] == pytest.approx(VENUE_LON)

            # Server records really are in this payload, so the absence of
            # their GPS is a meaningful assertion rather than a vacuous one.
            assert body["assignments"], "expected assigned servers in the detail payload"
            assigned_ids = {a["server_id"] for a in body["assignments"]}
            assert {driver_id, passenger_id} <= assigned_ids
            assert body["transport"]["groups"], "expected a confirmed transport group"
            group = body["transport"]["groups"][0]
            assert group["driver_name"]
            assert group["passengers"]

            # ...and none of it carries a raw fix.
            _assert_no_server_gps(body, "GET /api/events/{id}")
        finally:
            await self._teardown(event_id, driver_id, passenger_id, vehicle_id, skill)

    def test_response_models_declare_no_server_gps_field(self):
        """Static net over every server-data-bearing endpoint.

        Reads the live routing table, so this fails both when an existing model
        grows a GPS field and when a new server-facing endpoint is added.
        """
        checked = 0
        for path, method in SERVER_DATA_ENDPOINTS:
            model = _response_model_for(path, method)
            assert model is not None, f"no response_model registered for {method} {path}"
            declared = dict(_walk_model(model))
            for where, field in declared.items():
                if field not in SERVER_GPS_FIELDS:
                    continue
                assert where in ALLOWED_VENUE_PATHS, (
                    f"{method} {path}: response model declares raw GPS field "
                    f"'{field}' at {where}"
                )
            if path == "/api/events/{event_id}":
                # The allowlist must stay honest: the venue really is declared.
                assert "$.event.latitude" in declared
                assert "$.event.longitude" in declared
            checked += 1
        assert checked == len(SERVER_DATA_ENDPOINTS)

    def test_server_location_is_only_reachable_through_the_is_verified_flag(self):
        """server_locations exposes a boolean, never the coordinates."""
        from app.models.servers import ServerLocationResponse

        fields = set(ServerLocationResponse.model_fields)
        assert fields == {"city", "area", "is_verified"}
        assert not (fields & SERVER_GPS_FIELDS)

    async def test_urgent_offer_generation_never_returns_raw_server_gps(self):
        """The urgent path is checked at the engine level.

        Step 24C-D-3 fixed the response contract on this endpoint (it emitted
        raw `id` rows where UrgentGenerateResponse declares `offer_id`, so it
        500'd whenever a real offer was generated). The HTTP-level regression
        for that now lives in tests/test_urgent_offers.py; this test keeps the
        engine-level GPS assertion so the urgent path stays covered here too.
        """
        from app.services.urgent_engine import generate_urgent_offers

        event_id, driver_id, passenger_id, vehicle_id, skill = await self._seed_full_event(day=28)
        try:
            result = await generate_urgent_offers(event_id)
            assert "error" not in result, result
            offers = result.get("offers") or []
            assert offers, "expected at least one urgent offer to inspect"
            _assert_no_server_gps(result, "generate_urgent_offers")
        finally:
            await self._teardown(event_id, driver_id, passenger_id, vehicle_id, skill)
