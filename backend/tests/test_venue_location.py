"""Step 24C-D-4: venue location correctness and exact/approximate transparency.

Covers:
  A. cities.latitude / cities.longitude schema and constraints.
  B. The three-step location resolution hierarchy.
  C. has_exact_location exposure across the API.
  D. Transport route-distance semantics shared by recommendation and confirmation.

The invariant that must never regress: a server's personal GPS position is
NEVER used as an event venue, at any level of the hierarchy.
"""

import uuid
from datetime import datetime

import pytest

from app.core.database import get_pool
from app.core.config import settings
from app.main import app
from app.utils.event_utils import (
    LocationSource,
    resolve_event_location,
    resolve_event_location_detail,
)
from app.utils.selection_utils import haversine_km, route_distance_km

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"

# Venue coordinates (Paris) and a city reference that is far away (Tunis), so a
# test can never pass by accident if one source is silently used for another.
EXACT_LAT, EXACT_LON = 48.8566, 2.3522
# City reference is deliberately distinct from the venue but in the same
# metro area, so a city-based route stays plausible while a global-fallback
# route (Tunis, the configured default) is ~2300 km away.
CITY_LAT, CITY_LON = 48.86000, 2.36000

# Distinctive server GPS values, placed near the venue so a venue-based route
# is short. The event's OWN venue coordinates are public by design, so privacy
# is asserted on these private values and on the GPS-shaped payload keys, never
# on the bare `latitude`/`longitude` names.
DRIVER_GPS = (48.87001, 2.35002)
PASSENGER_GPS = (48.87503, 2.36004)

SERVER_GPS_FIELDS = frozenset(
    {
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


def _assert_no_server_gps(url, payload):
    """Neither GPS coordinates nor GPS-shaped keys may reach a client."""
    serialized = str(payload)
    for lat, lon in (DRIVER_GPS, PASSENGER_GPS):
        for value in (f"{lat}", f"{lon}"):
            assert value not in serialized, f"server GPS {value} leaked by {url}"
    for field in SERVER_GPS_FIELDS:
        assert field not in serialized, f"{field} leaked by {url}"


async def _book_staff(event_id, server_id, role="Guest"):
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


def _admin_headers():
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_event(
    city_id,
    latitude=None,
    longitude=None,
    is_urgent=False,
    day=12,
    status="PLANNED",
):
    event_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO events (
                id, name, client_name, city_id, address, latitude, longitude,
                start_datetime, end_datetime, guest_count, event_type, status, is_urgent
            )
            VALUES ($1, 'Location Event', 'Location Client', $2, '5 Venue Road',
                    $3, $4, $5, $6, 40, 'WEDDING', $7, $8)
            """,
            event_id,
            city_id,
            latitude,
            longitude,
            datetime(2025, 7, day, 10, 0, 0),
            datetime(2025, 7, day, 16, 0, 0),
            status,
            is_urgent,
        )
    return str(event_id), event_id


async def _set_city_coords(city_id, latitude, longitude):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE cities SET latitude = $2, longitude = $3 WHERE id = $1",
            city_id,
            latitude,
            longitude,
        )


async def _restore_city_coords(city_id):
    await _set_city_coords(city_id, None, None)


async def _create_skill():
    name = f"LocSkill-{uuid.uuid4().hex[:12]}"
    skill_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO skills (id, name) VALUES ($1, $2)", skill_id, name)
    return name, skill_id


async def _create_server_with_gps(skill_id, day, latitude=DRIVER_GPS[0], longitude=DRIVER_GPS[1]):
    server_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO servers (id, first_name, last_name, email, phone, gender, city_id, years_experience)
            VALUES ($1, 'Loc', 'Candidate', $2, '+21600000000', 'MALE',
                    (SELECT id FROM cities LIMIT 1), 5)
            """,
            server_id,
            f"{server_id}@example.org",
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
            datetime(2025, 7, day, 0, 0, 0),
            datetime(2025, 7, day, 23, 59, 0),
        )
        await conn.execute(
            """
            INSERT INTO server_locations (server_id, city_id, latitude, longitude, area, is_verified, is_current)
            VALUES ($1, (SELECT id FROM cities LIMIT 1), $2, $3, 'Test Area', TRUE, TRUE)
            """,
            server_id,
            latitude,
            longitude,
        )
    return server_id


async def _create_vehicle(server_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO vehicles (owner_server_id, vehicle_type, brand, model, seats_total, can_transport_coworkers, is_active)
            VALUES ($1, 'CAR', 'Loc', 'Car', 4, TRUE, TRUE)
            RETURNING id
            """,
            server_id,
        )


async def _create_requirement(event_id, role_name):
    req_id = uuid.uuid4()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_requirements (id, event_id, role_name, quantity, minimum_skill_level, minimum_experience)
            VALUES ($1, $2, $3, 1, 1, 0)
            """,
            req_id,
            event_id,
            role_name,
        )
    return str(req_id)


async def _cleanup(events, servers, skills):
    pool = await get_pool()
    async with pool.acquire() as conn:
        for event_id in events:
            await conn.execute("DELETE FROM urgent_event_offers WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM transport_passengers WHERE transport_group_id IN (SELECT id FROM transport_groups WHERE event_id = $1)", event_id)
            await conn.execute("DELETE FROM transport_groups WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_staff WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM event_requirements WHERE event_id = $1", event_id)
            await conn.execute("DELETE FROM events WHERE id = $1", event_id)
        for server_id in servers:
            await conn.execute("DELETE FROM server_locations WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM server_availability WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM server_skills WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM event_staff WHERE server_id = $1", server_id)
            await conn.execute("DELETE FROM vehicles WHERE owner_server_id = $1", server_id)
            await conn.execute("DELETE FROM servers WHERE id = $1", server_id)
        for skill in skills:
            await conn.execute("DELETE FROM skills WHERE name = $1", skill)


# ------------------------------------------------------- A. city coordinates


class TestCityCoordinateSchema:
    async def test_columns_exist_and_are_nullable(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'cities' AND column_name IN ('latitude', 'longitude')"
            )
        assert {r["column_name"] for r in rows} == {"latitude", "longitude"}
        assert all(r["is_nullable"] == "YES" for r in rows)

    async def test_a_city_without_coordinates_stays_without_coordinates(self):
        """The migration must not fabricate coordinates for existing rows."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO cities (id, name) VALUES ($1, $2)",
                city_id,
                "LocNoCoords",
            )
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT latitude, longitude FROM cities WHERE id = $1", city_id
                )
            assert row["latitude"] is None
            assert row["longitude"] is None
        finally:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM cities WHERE id = $1", city_id)

    async def test_valid_coordinates_are_accepted(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        try:
            await _set_city_coords(city_id, 36.7529, 10.2222)
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT latitude, longitude FROM cities WHERE id = $1", city_id
                )
            assert float(row["latitude"]) == pytest.approx(36.7529)
            assert float(row["longitude"]) == pytest.approx(10.2222)
        finally:
            await _restore_city_coords(city_id)

    async def test_invalid_latitude_is_rejected(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        try:
            with pytest.raises(Exception):
                await _set_city_coords(city_id, 91.0, 10.0)
        finally:
            await _restore_city_coords(city_id)

    async def test_invalid_longitude_is_rejected(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        try:
            with pytest.raises(Exception):
                await _set_city_coords(city_id, 36.0, 181.0)
        finally:
            await _restore_city_coords(city_id)

    async def test_half_a_coordinate_pair_is_rejected(self):
        """A lone coordinate must never be interpreted as origin (0, 0)."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        try:
            with pytest.raises(Exception):
                await _set_city_coords(city_id, 36.0, None)
        finally:
            await _restore_city_coords(city_id)


# -------------------------------------------------- B. resolution hierarchy


class TestLocationResolutionHierarchy:
    def test_exact_event_coordinates_win(self):
        detail = resolve_event_location_detail(
            {
                "latitude": EXACT_LAT,
                "longitude": EXACT_LON,
                "city_latitude": CITY_LAT,
                "city_longitude": CITY_LON,
            }
        )
        assert detail.source is LocationSource.EXACT_EVENT
        assert detail.has_exact_location is True
        assert (detail.latitude, detail.longitude) == (EXACT_LAT, EXACT_LON)

    def test_city_reference_is_used_when_event_has_no_coordinates(self):
        detail = resolve_event_location_detail(
            {
                "latitude": None,
                "longitude": None,
                "city_latitude": CITY_LAT,
                "city_longitude": CITY_LON,
            }
        )
        assert detail.source is LocationSource.CITY_REFERENCE
        assert detail.has_exact_location is False
        assert (detail.latitude, detail.longitude) == (CITY_LAT, CITY_LON)

    def test_global_fallback_is_the_last_resort(self):
        detail = resolve_event_location_detail(
            {"latitude": None, "longitude": None, "city_latitude": None, "city_longitude": None}
        )
        assert detail.source is LocationSource.GLOBAL_FALLBACK
        assert detail.has_exact_location is False
        assert detail.latitude == settings.DEFAULT_EVENT_LATITUDE
        assert detail.longitude == settings.DEFAULT_EVENT_LONGITUDE

    def test_half_an_event_coordinate_pair_falls_through_to_the_city(self):
        detail = resolve_event_location_detail(
            {
                "latitude": EXACT_LAT,
                "longitude": None,
                "city_latitude": CITY_LAT,
                "city_longitude": CITY_LON,
            }
        )
        assert detail.source is LocationSource.CITY_REFERENCE
        assert detail.has_exact_location is False

    def test_missing_event_falls_back_rather_than_raising(self):
        detail = resolve_event_location_detail(None)
        assert detail.source is LocationSource.GLOBAL_FALLBACK
        assert detail.has_exact_location is False

    def test_server_gps_keys_are_never_consumed_by_the_resolver(self):
        """server_locations-shaped keys must be ignored entirely."""
        detail = resolve_event_location_detail(
            {
                "latitude": None,
                "longitude": None,
                "current_latitude": EXACT_LAT,
                "current_longitude": EXACT_LON,
                "pickup_latitude": EXACT_LAT,
                "pickup_longitude": EXACT_LON,
            }
        )
        assert detail.source is LocationSource.GLOBAL_FALLBACK
        assert detail.latitude == settings.DEFAULT_EVENT_LATITUDE
        assert detail.latitude != EXACT_LAT

    def test_three_tuple_helper_stays_backward_compatible(self):
        assert resolve_event_location({"latitude": EXACT_LAT, "longitude": EXACT_LON}) == (
            EXACT_LAT,
            EXACT_LON,
            True,
        )
        assert resolve_event_location({}) == (
            settings.DEFAULT_EVENT_LATITUDE,
            settings.DEFAULT_EVENT_LONGITUDE,
            False,
        )


class TestLocationHierarchyThroughTheApi:
    async def test_exact_event_coordinates_report_exact(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        await _set_city_coords(city_id, CITY_LAT, CITY_LON)
        event_id, _ = await _create_event(city_id, latitude=EXACT_LAT, longitude=EXACT_LON)
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            assert event["latitude"] == pytest.approx(EXACT_LAT)
            assert event["has_exact_location"] is True
        finally:
            await _cleanup([event_id], [], [])
            await _restore_city_coords(city_id)

    async def test_city_reference_reports_approximate(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        await _set_city_coords(city_id, CITY_LAT, CITY_LON)
        event_id, _ = await _create_event(city_id)
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            assert event["latitude"] is None
            assert event["has_exact_location"] is False
        finally:
            await _cleanup([event_id], [], [])
            await _restore_city_coords(city_id)

    async def test_global_fallback_reports_approximate(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        event_id, _ = await _create_event(city_id)
        try:
            r = client.get(f"/api/events/{event_id}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            assert event["latitude"] is None
            assert event["has_exact_location"] is False
        finally:
            await _cleanup([event_id], [], [])

    async def test_staff_recommendation_reports_exactness(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        skill, skill_id = await _create_skill()
        server_id = await _create_server_with_gps(skill_id, day=14)
        event_id, _ = await _create_event(city_id, latitude=EXACT_LAT, longitude=EXACT_LON, day=14)
        await _create_requirement(event_id, skill)
        try:
            r = client.post(
                f"/api/events/{event_id}/generate-staff", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["event"]["has_exact_location"] is True
        finally:
            await _cleanup([event_id], [server_id], [skill])


# ------------------------------------------------------ D. transport distance


class TestRouteDistanceHelper:
    def test_empty_and_single_point_routes_are_zero(self):
        assert route_distance_km([]) == 0.0
        assert route_distance_km([(36.8, 10.1)]) == 0.0

    def test_route_is_the_sum_of_ordered_legs(self):
        a, b, c = (36.8, 10.1), (36.9, 10.2), (37.0, 10.3)
        expected = round(haversine_km(*a, *b) + haversine_km(*b, *c), 6)
        assert route_distance_km([a, b, c]) == pytest.approx(expected)

    def test_no_leg_is_counted_twice(self):
        """A driver -> passenger -> venue route is not a driver-to-all sum."""
        driver, pickup, venue = (36.8, 10.1), (36.9, 10.2), (37.0, 10.3)
        chained = route_distance_km([driver, pickup, venue])
        star = haversine_km(*driver, *pickup) + haversine_km(*driver, *venue)
        assert chained < star, "chained route must not re-measure legs from the driver"


class TestTransportDistanceSemantics:
    async def _seed_transport_event(self, day, venue_lat, venue_lon, city_coords=False):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        if city_coords:
            await _set_city_coords(city_id, CITY_LAT, CITY_LON)
        skill, skill_id = await _create_skill()
        driver_id = await _create_server_with_gps(
            skill_id, day=day, latitude=DRIVER_GPS[0], longitude=DRIVER_GPS[1]
        )
        passenger_id = await _create_server_with_gps(
            skill_id, day=day, latitude=PASSENGER_GPS[0], longitude=PASSENGER_GPS[1]
        )
        await _create_vehicle(driver_id)
        event_id, _ = await _create_event(
            city_id, latitude=venue_lat, longitude=venue_lon, day=day, status="CONFIRMED"
        )
        await _create_requirement(event_id, skill)
        # Transport requires both crew members to be booked on the event.
        await _book_staff(event_id, driver_id, role="Driver")
        await _book_staff(event_id, passenger_id, role="Guest")
        return event_id, city_id, driver_id, passenger_id, skill, city_coords

    async def test_exact_venue_route_includes_the_final_venue_leg(self):
        event_id, city_id, driver_id, passenger_id, skill, _ = await self._seed_transport_event(
            day=20, venue_lat=EXACT_LAT, venue_lon=EXACT_LON
        )
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": str(driver_id),
                            "passengers": [{"server_id": str(passenger_id), "pickup_order": 1}],
                        }
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            group = r.json()["groups"][0]
            assert group["has_exact_location"] is True
            assert group["estimated_route_distance_km"] is not None
            assert group["estimated_route_distance_km"] > 0
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [skill])

    async def test_city_fallback_route_still_includes_the_final_leg(self):
        event_id, city_id, driver_id, passenger_id, skill, used_city = await self._seed_transport_event(
            day=21, venue_lat=None, venue_lon=None, city_coords=True
        )
        assert used_city
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": str(driver_id),
                            "passengers": [{"server_id": str(passenger_id), "pickup_order": 1}],
                        }
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            group = r.json()["groups"][0]
            assert group["has_exact_location"] is False
            assert group["estimated_route_distance_km"] > 0

            # The stored destination must be the CITY reference, not the
            # global fallback and never the driver's own GPS.
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT destination_latitude, destination_longitude, destination_label "
                    "FROM transport_groups WHERE event_id = $1",
                    event_id,
                )
            assert float(row["destination_latitude"]) == pytest.approx(CITY_LAT, abs=0.01)
            assert float(row["destination_longitude"]) == pytest.approx(CITY_LON, abs=0.01)
            assert "position approximative" in row["destination_label"]
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [skill])
            await _restore_city_coords(city_id)

    async def test_global_fallback_route_still_includes_the_final_leg(self):
        event_id, city_id, driver_id, passenger_id, skill, _ = await self._seed_transport_event(
            day=22, venue_lat=None, venue_lon=None
        )
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": str(driver_id),
                            "passengers": [{"server_id": str(passenger_id), "pickup_order": 1}],
                        }
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            group = r.json()["groups"][0]
            assert group["has_exact_location"] is False
            assert group["estimated_route_distance_km"] > 0

            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT destination_latitude, destination_longitude "
                    "FROM transport_groups WHERE event_id = $1",
                    event_id,
                )
            assert float(row["destination_latitude"]) == pytest.approx(
                settings.DEFAULT_EVENT_LATITUDE, abs=0.01
            )
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [skill])

    async def test_recommendation_and_confirmation_agree_on_the_destination(self):
        """Both endpoints must measure from the venue, not the global fallback.

        Regression: `recommendation["event"]` is a trimmed selection summary
        with no coordinates, so resolving the venue from it silently sent every
        recommended distance to the technical fallback ~1500 km away.
        """
        event_id, city_id, driver_id, passenger_id, skill, _ = await self._seed_transport_event(
            day=23, venue_lat=EXACT_LAT, venue_lon=EXACT_LON
        )
        try:
            headers = _admin_headers()
            recommended = client.post(
                f"/api/events/{event_id}/recommend-transport", headers=headers
            )
            assert recommended.status_code == 200, recommended.text
            rec = recommended.json()
            assert rec.get("transport_status") == "SUCCESS", rec
            assert rec["has_exact_location"] is True
            assert rec["groups"], "recommendation must expose per-group distances"
            assert all(g["has_exact_location"] is True for g in rec["groups"])

            confirmed = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": str(driver_id),
                            "passengers": [{"server_id": str(passenger_id), "pickup_order": 1}],
                        }
                    ]
                },
                headers=headers,
            )
            assert confirmed.status_code == 200, confirmed.text
            group = confirmed.json()["groups"][0]
            assert group["has_exact_location"] is True

            # The crew differs between the two endpoints, so exact equality is
            # not meaningful. What must hold is that both measure from the same
            # venue: a fallback-based distance would be ~1500 km, not ~1500 m.
            distances = [g["estimated_route_distance_km"] for g in rec["groups"]]
            distances.append(group["estimated_route_distance_km"])
            for distance in distances:
                assert 0 < distance < 500, distance
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [skill])

    async def test_legacy_distance_field_agrees_across_recommendation_and_confirmation(self):
        """`estimated_distance_km` must mean the same thing on both endpoints.

        Regression: the recommendation omitted the final venue leg while the
        confirmation included (and persisted) it, so the number a manager saw
        before confirming changed once they confirmed the same group.
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        skill, skill_id = await _create_skill()
        driver_id = await _create_server_with_gps(
            skill_id, day=27, latitude=DRIVER_GPS[0], longitude=DRIVER_GPS[1]
        )
        p1_id = await _create_server_with_gps(
            skill_id, day=27, latitude=PASSENGER_GPS[0], longitude=PASSENGER_GPS[1]
        )
        p2_id = await _create_server_with_gps(skill_id, day=27, latitude=48.88105, longitude=2.37006)
        await _create_vehicle(driver_id)
        event_id, _ = await _create_event(
            city_id, latitude=EXACT_LAT, longitude=EXACT_LON, day=27, status="CONFIRMED"
        )
        await _create_requirement(event_id, skill)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE event_requirements SET quantity = 3 WHERE event_id = $1", event_id
            )
        for sid in (driver_id, p1_id, p2_id):
            await _book_staff(event_id, sid, role="Guest")
        try:
            headers = _admin_headers()
            rec = client.post(f"/api/events/{event_id}/recommend-transport", headers=headers)
            assert rec.status_code == 200, rec.text
            rec_body = rec.json()
            assert rec_body.get("transport_status") == "SUCCESS", rec_body
            group = rec_body["groups"][0]
            assert len(group["passengers"]) == 2, "expected driver + 2 passengers"

            confirmed = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": group["driver"]["server_id"],
                            "passengers": [
                                {"server_id": p["server_id"], "pickup_order": p["pickup_order"]}
                                for p in group["passengers"]
                            ],
                        }
                    ]
                },
                headers=headers,
            )
            assert confirmed.status_code == 200, confirmed.text
            confirmed_group = confirmed.json()["groups"][0]

            # Both endpoints, same group, same meaning.
            assert confirmed_group["estimated_distance_km"] == pytest.approx(
                group["estimated_distance_km"], abs=0.05
            )
            assert confirmed_group["estimated_route_distance_km"] == pytest.approx(
                group["estimated_route_distance_km"], abs=0.05
            )

            # The legacy field is the pickup legs plus the final venue leg, so it
            # must be strictly larger than the pickup legs alone.
            pickup_legs = sum(p["distance_from_driver_km"] for p in group["passengers"])
            assert group["estimated_distance_km"] > pickup_legs
        finally:
            await _cleanup([event_id], [driver_id, p1_id, p2_id], [skill])

    async def test_legacy_distance_field_is_preserved_for_compatibility(self):
        event_id, city_id, driver_id, passenger_id, skill, _ = await self._seed_transport_event(
            day=24, venue_lat=EXACT_LAT, venue_lon=EXACT_LON
        )
        try:
            r = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": str(driver_id),
                            "passengers": [{"server_id": str(passenger_id), "pickup_order": 1}],
                        }
                    ]
                },
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            group = r.json()["groups"][0]
            # The historical field keeps its meaning and is still present.
            assert "estimated_distance_km" in group
            assert group["estimated_distance_km"] is not None
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [skill])


# --------------------------------------------- C. contract + privacy coverage


class TestExactnessExposureAndPrivacy:
    async def test_event_detail_transport_groups_expose_exactness_and_route(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        skill, skill_id = await _create_skill()
        driver_id = await _create_server_with_gps(skill_id, day=25)
        passenger_id = await _create_server_with_gps(
            skill_id, day=25, latitude=PASSENGER_GPS[0], longitude=PASSENGER_GPS[1]
        )
        await _create_vehicle(driver_id)
        event_id, _ = await _create_event(
            city_id, latitude=EXACT_LAT, longitude=EXACT_LON, day=25, status="CONFIRMED"
        )
        await _create_requirement(event_id, skill)
        await _book_staff(event_id, driver_id, role="Driver")
        await _book_staff(event_id, passenger_id, role="Guest")
        try:
            headers = _admin_headers()
            confirmed = client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": str(driver_id),
                            "passengers": [{"server_id": str(passenger_id), "pickup_order": 1}],
                        }
                    ]
                },
                headers=headers,
            )
            assert confirmed.status_code == 200, confirmed.text

            r = client.get(f"/api/events/{event_id}", headers=headers)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["event"]["has_exact_location"] is True
            groups = body["transport"]["groups"]
            assert groups, "expected a confirmed transport group"
            assert groups[0]["has_exact_location"] is True
            assert groups[0]["estimated_route_distance_km"] > 0
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [skill])

    async def test_no_response_exposes_raw_server_gps(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        skill, skill_id = await _create_skill()
        driver_id = await _create_server_with_gps(skill_id, day=26)
        passenger_id = await _create_server_with_gps(
            skill_id, day=26, latitude=PASSENGER_GPS[0], longitude=PASSENGER_GPS[1]
        )
        await _create_vehicle(driver_id)
        event_id, _ = await _create_event(
            city_id, latitude=EXACT_LAT, longitude=EXACT_LON, day=26, status="CONFIRMED"
        )
        await _create_requirement(event_id, skill)
        await _book_staff(event_id, driver_id, role="Driver")
        await _book_staff(event_id, passenger_id, role="Guest")
        try:
            headers = _admin_headers()
            client.post(
                f"/api/events/{event_id}/confirm-transport",
                json={
                    "groups": [
                        {
                            "driver_server_id": str(driver_id),
                            "passengers": [{"server_id": str(passenger_id), "pickup_order": 1}],
                        }
                    ]
                },
                headers=headers,
            )
            probes = [
                f"/api/events/{event_id}",
                f"/api/events/{event_id}/operations",
                f"/api/events/{event_id}/urgent-status",
                f"/api/servers/{driver_id}",
                "/api/servers?location_verified=true",
            ]
            for url in probes:
                r = client.get(url, headers=headers)
                assert r.status_code == 200, f"{url} -> {r.status_code}"
                _assert_no_server_gps(url, r.json())

            rec = client.post(f"/api/events/{event_id}/recommend-transport", headers=headers)
            assert rec.status_code == 200, rec.text
            _assert_no_server_gps("recommend-transport", rec.json())
        finally:
            await _cleanup([event_id], [driver_id, passenger_id], [skill])

    def test_location_source_is_internal_only(self):
        """Clients receive has_exact_location, never the internal resolver enum."""
        from app.models.events import (
            EventDetailEventResponse,
            EventDetailTransportGroupResponse,
        )
        from app.models.transport_assignment import TransportRecommendationResponse

        models = [
            EventDetailEventResponse,
            EventDetailTransportGroupResponse,
            TransportRecommendationResponse,
        ]
        for model in models:
            fields = set(model.model_fields)
            assert "has_exact_location" in fields, f"{model.__name__} must expose exactness"
            for field in fields:
                assert "source" not in field, f"{model.__name__} leaks internal source as {field}"
                assert "resolution" not in field, f"{model.__name__} leaks resolver detail"
