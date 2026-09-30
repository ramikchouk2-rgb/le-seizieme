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
):
    event_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO events (
                id, name, client_name, city_id, address, latitude, longitude,
                start_datetime, end_datetime, guest_count, event_type, status
            )
            VALUES (
                $1, $2, $3, (SELECT id FROM cities LIMIT 1), $4, $5, $6,
                $7, $8, 50, 'TEST', $9
            )
            """,
            event_id,
            f"Coordinate Event {event_id}",
            "Coordinate Client",
            address,
            latitude,
            longitude,
            datetime(2025, 5, day, 10, 0, 0),
            datetime(2025, 5, day, 14, 0, 0),
            status,
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


class TestServerGpsNotExposed:
    async def test_server_endpoints_never_return_raw_gps(self):
        server_id, _, _ = await _create_server_with_location(48.8566, 2.3522)
        headers = _admin_headers()
        try:
            for url in (
                "/api/servers?location_verified=true",
                f"/api/servers/{server_id}",
            ):
                r = client.get(url, headers=headers)
                assert r.status_code == 200, f"{url} -> {r.status_code}"
                body = r.json()
                serialized = str(body)
                for banned in ("latitude", "longitude", "48.8566", "2.3522"):
                    assert banned not in serialized, f"{banned} leaked by {url}"
        finally:
            await _cleanup([], [server_id], [server_id])

    async def test_staff_recommendation_never_returns_raw_gps(self):
        server_id, skill, skill_id = await _create_server_with_location(48.8566, 2.3522)
        event_id = await _create_event(latitude=VENUE_LAT, longitude=VENUE_LON, day=23)
        req_id = await _create_requirement(event_id, skill, skill_id)
        try:
            r = client.post(
                f"/api/events/{event_id}/generate-staff", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            serialized = str(r.json())
            for banned in ("current_latitude", "current_longitude", "48.8566", "2.3522"):
                assert banned not in serialized, f"{banned} leaked by staff recommendations"
        finally:
            await _cleanup([event_id], [server_id], [server_id])
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM skills WHERE name = $1", skill)
