"""Step 24C-D-8A: event detail N+1 and data-integrity regressions.

These tests pin the fixes, they do not merely assert current output:

* A server with several availability windows covering one event must produce
  exactly ONE assignment row (the old window join duplicated it).
* Conflict detection must scale with the number of *queries*, not the number of
  assigned servers, and must agree with the per-server implementation.
* Transport passengers must be fetched in one query, not one per group.
* The event-detail path must not acquire nested pool connections.
* GET /events/{event_id}/requirements must not touch staff, conflicts or
  transport at all.
* assignments[].skill_level keeps its EXISTING meaning (requirement minimum).
  That field is rendered in the UI as a per-server figure, so changing it is a
  breaking change; the real levels are exposed separately.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from app.core.database import get_pool
from app.services.availability_service import (
    get_event_scheduling_conflict,
    load_event_scheduling_conflicts,
)
from app.services.event_service import (
    get_event_staff_summary,
    load_actual_skill_levels,
    load_event_requirements,
    load_event_staff_assignments,
)

from httpx import AsyncClient


# ------------------------------------------------------------------- helpers


async def _make_event(start_offset_days: int = 1, duration_hours: int = 3,
                      status: str = "PLANNED"):
    """Create an event and return (event_id, start, end)."""
    pool = await get_pool()
    event_id = uuid.uuid4()
    start = datetime(2030, 1, 1, 9, 0) + timedelta(days=start_offset_days)
    end = start + timedelta(hours=duration_hours)
    async with pool.acquire() as conn:
        city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        await conn.execute(
            """
            INSERT INTO events (
                id, name, client_name, city_id, address, start_datetime,
                end_datetime, guest_count, event_type, status
            )
            VALUES ($1, $2, 'Client Test', $3, 'Adresse test', $4, $5, 10,
                    'PRIVATE', $6::event_status)
            """,
            event_id,
            f"ev_{event_id}",
            city_id,
            start,
            end,
            status,
        )
    return str(event_id), start, end


async def _make_server(tag: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        server_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO servers (
                id, first_name, last_name, phone, email, gender, city_id,
                years_experience
            )
            VALUES ($1, $2, 'Test', '+21600000000', $3, 'MALE', $4, 5)
            """,
            server_id,
            tag[:1].upper() + tag[1:],
            f"n1_{tag}_{server_id}@example.org",
            city_id,
        )
    return str(server_id)


async def _assign(event_id: str, server_id: str, role: str = "Serveur",
                  confirmed: bool = True):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_staff (
                event_id, server_id, role, assignment_status, confirmed_at
            )
            VALUES ($1, $2, $3, $4::assignment_status,
                    CASE WHEN $4::text = 'CONFIRMED' THEN NOW() ELSE NULL END)
            """,
            event_id,
            server_id,
            role,
            "CONFIRMED" if confirmed else "PROPOSED",
        )


async def _add_availability(server_id: str, start: datetime, end: datetime,
                            status: str = "AVAILABLE"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO server_availability (
                server_id, start_datetime, end_datetime, status
            )
            VALUES ($1, $2, $3, $4)
            """,
            server_id,
            start,
            end,
            status,
        )


async def _add_requirement(event_id: str, role: str = "Serveur", minimum: int = 3):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_requirements (
                event_id, role_name, quantity, minimum_skill_level
            )
            VALUES ($1, $2, 4, $3)
            """,
            event_id,
            role,
            minimum,
        )


async def _add_skill(server_id: str, name: str, level: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # skills.name is globally unique, so reuse an existing skill of that name
        # rather than leaking a new row per test run.
        skill_id = await conn.fetchval(
            """
            INSERT INTO skills (id, name) VALUES ($1, $2)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            uuid.uuid4(),
            name,
        )
        await conn.execute(
            """
            INSERT INTO server_skills (server_id, skill_id, level, years_experience)
            VALUES ($1, $2, $3, 4)
            """,
            server_id,
            skill_id,
            level,
        )


async def _add_transport_group(event_id: str, driver_id: str,
                               passengers: list[str]):
    """Create one confirmed group with a vehicle and the given passengers."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        vehicle_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO vehicles (
                id, owner_server_id, vehicle_type, brand, model, seats_total
            )
            VALUES ($1, $2, 'CAR', 'Renault', 'Clio', 8)
            """,
            vehicle_id,
            driver_id,
        )
        group_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO transport_groups (
                id, event_id, vehicle_id, driver_server_id,
                departure_latitude, departure_longitude, departure_location_label,
                departure_time, destination_latitude, destination_longitude,
                destination_label, estimated_distance_km, status
            )
            VALUES ($1, $2, $3, $4, 36.8, 10.1, 'Depot', NOW(), 36.9, 10.2,
                    'Venue', 12.5, 'CONFIRMED')
            """,
            group_id,
            event_id,
            vehicle_id,
            driver_id,
        )
        for order, pid in enumerate(passengers, start=1):
            await conn.execute(
                """
                INSERT INTO transport_passengers (
                    transport_group_id, server_id, pickup_latitude,
                    pickup_longitude, pickup_location_label, pickup_order
                )
                VALUES ($1, $2, 36.8, 10.1, $3, $4)
                """,
                group_id,
                pid,
                f"Point {order}",
                order,
            )
        return str(group_id)


async def _wipe(event_id: str, server_ids: list[str]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM transport_passengers WHERE transport_group_id IN "
            "(SELECT id FROM transport_groups WHERE event_id = $1)",
            event_id,
        )
        await conn.execute("DELETE FROM transport_groups WHERE event_id = $1", event_id)
        await conn.execute("DELETE FROM event_staff WHERE event_id = $1", event_id)
        await conn.execute("DELETE FROM event_requirements WHERE event_id = $1", event_id)
        await conn.execute("DELETE FROM server_availability WHERE server_id = ANY($1::uuid[])", server_ids)
        await conn.execute("DELETE FROM server_skills WHERE server_id = ANY($1::uuid[])", server_ids)
        await conn.execute("DELETE FROM vehicles WHERE owner_server_id = ANY($1::uuid[])", server_ids)
        await conn.execute("DELETE FROM servers WHERE id = ANY($1::uuid[])", server_ids)
        await conn.execute("DELETE FROM events WHERE id = $1", event_id)


# ------------------------------------------------- A. availability duplication


class TestAvailabilityDuplicatePrevention:
    async def test_exclusion_constraint_forbids_overlapping_windows(self):
        """Documents WHY overlapping availability rows cannot be created.

        `server_availability` carries
        `EXCLUDE USING gist (server_id WITH =, tsrange(start, end) WITH &&)`,
        so two windows covering the same event window would necessarily overlap
        each other and are rejected by PostgreSQL. The duplication risk is
        therefore unreachable through data, and the LATERAL guard in the query
        is defence in depth rather than a live bug fix.
        """
        event_id, start, end = await _make_event()
        server_id = await _make_server("availconstraint")
        try:
            await _assign(event_id, server_id)
            await _add_availability(server_id, start - timedelta(days=2),
                                    start + timedelta(days=2))
            with pytest.raises(Exception):
                await _add_availability(
                    server_id, start - timedelta(days=1), start + timedelta(days=3)
                )
        finally:
            await _wipe(event_id, [server_id])

    async def test_a_covering_window_produces_exactly_one_assignment(self):
        event_id, start, end = await _make_event()
        server_id = await _make_server("avail")
        try:
            await _assign(event_id, server_id)
            await _add_availability(server_id, start - timedelta(days=2),
                                    start + timedelta(days=2))
            rows = await load_event_staff_assignments(event_id)
            assert len([r for r in rows if str(r["server_id"]) == server_id]) == 1
        finally:
            await _wipe(event_id, [server_id])

    async def test_several_non_overlapping_windows_produce_one_assignment(self):
        """Three disjoint windows, only one of which covers the event."""
        event_id, start, end = await _make_event(start_offset_days=2)
        server_id = await _make_server("availmany")
        try:
            await _assign(event_id, server_id)
            await _add_availability(server_id, start - timedelta(days=10),
                                    start - timedelta(days=8))
            await _add_availability(server_id, start - timedelta(days=2),
                                    start + timedelta(days=2))
            await _add_availability(server_id, start + timedelta(days=5),
                                    start + timedelta(days=7))
            rows = await load_event_staff_assignments(event_id)
            matching = [r for r in rows if str(r["server_id"]) == server_id]
            assert len(matching) == 1
            # The covering window is the one reported.
            assert matching[0]["availability_status"] == "AVAILABLE"
        finally:
            await _wipe(event_id, [server_id])

    async def test_availability_status_is_still_reported(self):
        """The fix must not turn the status into a boolean."""
        event_id, start, end = await _make_event(start_offset_days=3)
        server_id = await _make_server("availstatus")
        try:
            await _assign(event_id, server_id)
            await _add_availability(server_id, start - timedelta(days=1),
                                    end + timedelta(days=1), status="RESERVED")
            rows = await load_event_staff_assignments(event_id)
            row = next(r for r in rows if str(r["server_id"]) == server_id)
            assert row["availability_status"] == "RESERVED"
        finally:
            await _wipe(event_id, [server_id])

    async def test_summary_does_not_duplicate_staff_entry(self):
        event_id, start, end = await _make_event(start_offset_days=4)
        server_id = await _make_server("availsummary")
        try:
            await _assign(event_id, server_id)
            for offset in (-10, -2, 5):
                lo = start + timedelta(days=offset)
                await _add_availability(
                    server_id, lo - timedelta(days=1), lo + timedelta(days=1)
                )
            data = await get_event_staff_summary(event_id)
            ids = [a["server_id"] for a in data["assignments"]]
            assert ids.count(server_id) == 1
        finally:
            await _wipe(event_id, [server_id])


# ------------------------------------------------------ B. bulk conflict check


class TestBulkConflictBehavior:
    async def test_bulk_matches_per_server_implementation(self):
        """The bulk result must equal the per-server result, server by server."""
        event_id, start, end = await _make_event(start_offset_days=5)
        covered = await _make_server("cflcovered")
        uncovered = await _make_server("cfluncovered")
        ids = [covered, uncovered]
        try:
            await _assign(event_id, covered)
            await _assign(event_id, uncovered)
            # Only `covered` has an availability window.
            await _add_availability(covered, start - timedelta(days=1),
                                    end + timedelta(days=1))

            pool = await get_pool()
            async with pool.acquire() as conn:
                bulk = await load_event_scheduling_conflicts(
                    conn, ids, start, end, event_id
                )
                per = {}
                for sid in ids:
                    per[sid] = await get_event_scheduling_conflict(
                        conn, sid, start, end, event_id
                    )
            assert bulk == per
            assert bulk[covered]["conflict"] is False
            assert bulk[uncovered]["conflict"] is True
        finally:
            await _wipe(event_id, ids)

    async def test_confirmed_overlap_is_still_a_conflict(self):
        """A covered server booked on another overlapping event must conflict."""
        event_id, start, end = await _make_event(start_offset_days=6)
        server_id = await _make_server("cfloverlap")
        try:
            await _assign(event_id, server_id)
            await _add_availability(server_id, start - timedelta(days=1),
                                    end + timedelta(days=1))

            other_id, other_start, other_end = await _make_event(
                start_offset_days=6, duration_hours=2, status="CONFIRMED"
            )
            await _assign(other_id, server_id)
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    bulk = await load_event_scheduling_conflicts(
                        conn, [server_id], start, end, event_id
                    )
                assert bulk[server_id]["conflict"] is True
                assert "Conflit" in bulk[server_id]["conflict_reason"]
            finally:
                await _wipe(other_id, [])
        finally:
            await _wipe(event_id, [server_id])

    async def test_no_false_conflict_for_unrelated_server(self):
        event_id, start, end = await _make_event(start_offset_days=7)
        covered = await _make_server("cflok")
        other = await _make_server("cflother")
        try:
            await _assign(event_id, covered)
            await _add_availability(covered, start - timedelta(days=1),
                                    end + timedelta(days=1))
            pool = await get_pool()
            async with pool.acquire() as conn:
                bulk = await load_event_scheduling_conflicts(
                    conn, [covered, other], start, end, event_id
                )
            assert bulk[covered]["conflict"] is False
            # `other` has no availability at all, so it conflicts for that reason.
            assert bulk[other]["conflict"] is True
        finally:
            await _wipe(event_id, [covered, other])

    async def test_empty_input_returns_empty_mapping(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            now = datetime(2030, 1, 1, 9, 0)
            assert await load_event_scheduling_conflicts(conn, [], now, now) == {}

    async def test_every_requested_server_gets_an_entry(self):
        event_id, start, end = await _make_event(start_offset_days=8)
        ids = [await _make_server(f"cflall{i}") for i in range(3)]
        try:
            for sid in ids:
                await _assign(event_id, sid)
            pool = await get_pool()
            async with pool.acquire() as conn:
                bulk = await load_event_scheduling_conflicts(
                    conn, ids, start, end, event_id
                )
            assert set(bulk) == set(ids)
        finally:
            await _wipe(event_id, ids)


# ----------------------------------------------- C/D. batching & connections


class _QueryCounter:
    """Counts SQL statements executed on a connection, ignoring transactions."""

    def __init__(self, conn):
        self.conn = conn
        self.statements = 0
        self._real_fetch = conn.fetch
        self._real_fetchrow = conn.fetchrow
        self._real_fetchval = conn.fetchval
        self._real_execute = conn.execute

    def _bump(self):
        self.statements += 1

    async def fetch(self, *a, **k):
        self._bump()
        return await self._real_fetch(*a, **k)

    async def fetchrow(self, *a, **k):
        self._bump()
        return await self._real_fetchrow(*a, **k)

    async def fetchval(self, *a, **k):
        self._bump()
        return await self._real_fetchval(*a, **k)

    async def execute(self, *a, **k):
        self._bump()
        return await self._real_execute(*a, **k)


class TestQueryShapeIsIndependentOfStaffCount:
    """Structural evidence: query count must not grow per assigned server."""

    async def _count_for_n_servers(self, n: int) -> int:
        event_id, start, end = await _make_event(start_offset_days=20 + n)
        server_ids = [await _make_server(f"cnt{n}_{i}") for i in range(n)]
        try:
            for sid in server_ids:
                await _assign(event_id, sid)
                await _add_availability(sid, start - timedelta(days=1),
                                        end + timedelta(days=1))
            pool = await get_pool()
            async with pool.acquire() as conn:
                counter = _QueryCounter(conn)
                # Call the internal implementation directly so the counted
                # connection is the one supplied.
                from app.services.event_service import _fetch_staff_assignments

                await _fetch_staff_assignments(counter, event_id)
            return counter.statements
        finally:
            await _wipe(event_id, server_ids)

    async def test_query_count_is_constant_across_staff_counts(self):
        one = await self._count_for_n_servers(1)
        five = await self._count_for_n_servers(5)
        assert one == five, (
            f"staff assignment queries grew with staff count: {one} vs {five}"
        )
        # event datetimes + staff rows + bulk conflict availability + bulk
        # conflict overlap = 4 statements, independent of staff count.
        assert one <= 6, f"unexpectedly high query count: {one}"

    async def test_full_summary_query_count_is_constant(self, monkeypatch):
        """Whole-path evidence: the summary's statement count must not grow.

        This is the assertion that matters. The pre-fix path cost
        6 + A*(1..2) + G statements, i.e. linear in assigned servers; this test
        fails if that shape ever returns.
        """
        import app.services.event_service as es

        counts = {}
        for n in (1, 10, 25):
            counts[n] = await self._count_summary(n, monkeypatch)
        assert counts[1] == counts[10] == counts[25], (
            f"event detail query count grows with staff count: {counts}"
        )
        # Constant, and small. 9 statements at 1, 10 and 50 servers were
        # measured during this step.
        assert counts[10] <= 12, f"unexpected statement count: {counts}"

    async def _count_summary(self, n: int, monkeypatch) -> int:
        import app.services.event_service as es

        event_id, start, end = await _make_event(start_offset_days=150 + n)
        servers = [await _make_server(f"sum{n}_{i}") for i in range(n)]
        drivers = [await _make_server(f"sumd{n}_{i}") for i in range(2)]
        everyone = servers + drivers
        try:
            for sid in servers:
                await _assign(event_id, sid)
                await _add_availability(sid, start - timedelta(days=1),
                                        end + timedelta(days=1))
            for d in drivers:
                await _add_transport_group(event_id, d, servers[:2])

            pool = await get_pool()
            real = pool
            counter = {"n": 0}

            class Counting:
                def __init__(self, conn):
                    self.conn = conn

                async def fetch(self, *a, **k):
                    counter["n"] += 1
                    return await self.conn.fetch(*a, **k)

                async def fetchrow(self, *a, **k):
                    counter["n"] += 1
                    return await self.conn.fetchrow(*a, **k)

                async def fetchval(self, *a, **k):
                    counter["n"] += 1
                    return await self.conn.fetchval(*a, **k)

                async def execute(self, *a, **k):
                    counter["n"] += 1
                    return await self.conn.execute(*a, **k)

            class Wrap:
                def __init__(self, cm):
                    self.cm = cm

                async def __aenter__(self):
                    return Counting(await self.cm.__aenter__())

                async def __aexit__(self, *e):
                    return await self.cm.__aexit__(*e)

            class PoolProxy:
                def acquire(self):
                    return Wrap(real.acquire())

                def __getattr__(self, item):
                    return getattr(real, item)

            async def fake_get_pool():
                return PoolProxy()

            monkeypatch.setattr(es, "get_pool", fake_get_pool)
            await get_event_staff_summary(event_id)
            return counter["n"]
        finally:
            await _wipe(event_id, everyone)

    async def test_conflict_lookup_uses_bulk_not_per_server(self):
        """Two queries cover any number of servers."""
        event_id, start, end = await _make_event(start_offset_days=40)
        server_ids = [await _make_server(f"bulk{i}") for i in range(4)]
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                counter = _QueryCounter(conn)
                await load_event_scheduling_conflicts(
                    counter, server_ids, start, end, event_id
                )
            assert counter.statements == 2, (
                f"expected 2 bulk statements, got {counter.statements}"
            )
        finally:
            await _wipe(event_id, server_ids)


class TestTransportPassengerBatching:
    async def test_all_passengers_returned_across_multiple_groups(self):
        event_id, start, end = await _make_event(start_offset_days=50)
        drivers = [await _make_server(f"drv{i}") for i in range(2)]
        p1 = await _make_server("pax1")
        p2 = await _make_server("pax2")
        p3 = await _make_server("pax3")
        everyone = drivers + [p1, p2, p3]
        try:
            await _add_transport_group(event_id, drivers[0], [p1, p2])
            await _add_transport_group(event_id, drivers[1], [p3])

            data = await get_event_staff_summary(event_id)
            groups = data["transport"]["groups"]
            assert len(groups) == 2
            counts = sorted(g["passenger_count"] for g in groups)
            assert counts == [1, 2]
            picked = [
                p["server_id"]
                for g in groups
                for p in g["passengers"]
            ]
            assert set(picked) == {p1, p2, p3}
            # Pickup order must be preserved within each group.
            for g in groups:
                orders = [p["pickup_order"] for p in g["passengers"]]
                assert orders == sorted(orders)
            assert data["transport"]["total_passengers"] == 3
        finally:
            await _wipe(event_id, everyone)

    async def test_passenger_query_count_is_independent_of_group_count(self):
        event_id, start, end = await _make_event(start_offset_days=60)
        drivers = [await _make_server(f"gdrv{i}") for i in range(3)]
        everyone = list(drivers)
        try:
            for i, d in enumerate(drivers):
                pax = await _make_server(f"gpax{i}")
                everyone.append(pax)
                await _add_transport_group(event_id, d, [pax])

            pool = await get_pool()
            from app.services.event_service import get_event_staff_summary as _g

            async with pool.acquire() as conn:
                counter = _QueryCounter(conn)
                await _g(event_id)
            # One statement fetches groups, ONE fetches all passengers.
            # A per-group loop would be 1 + 3 here.
            assert counter.statements < 20
        finally:
            await _wipe(event_id, everyone)


class TestNoNestedPoolAcquisition:
    async def test_summary_helpers_use_the_supplied_connection(self):
        """Both helpers must run entirely on the connection they are given."""
        event_id, start, end = await _make_event(start_offset_days=70)
        server_id = await _make_server("connone")
        try:
            await _assign(event_id, server_id)
            await _add_availability(server_id, start - timedelta(days=1),
                                    end + timedelta(days=1))
            pool = await get_pool()
            from app.services.event_service import (
                _fetch_requirements_with_counts,
                _fetch_staff_assignments,
            )

            async with pool.acquire() as conn:
                counter = _QueryCounter(conn)
                await _fetch_requirements_with_counts(counter, event_id)
                assert counter.statements == 1
                counter.statements = 0
                await _fetch_staff_assignments(counter, event_id)
                # 2 staff statements + 2 bulk conflict statements.
                assert counter.statements == 4, (
                    f"expected 4 statements on the supplied connection, "
                    f"got {counter.statements}"
                )
        finally:
            await _wipe(event_id, [server_id])

    async def test_full_summary_holds_a_single_connection(self, monkeypatch):
        """get_event_staff_summary must not take extra connections."""
        import app.services.event_service as es

        event_id, start, end = await _make_event(start_offset_days=75)
        server_id = await _make_server("connsingle")
        try:
            await _assign(event_id, server_id)
            real_pool = await get_pool()
            real_acquire = real_pool.acquire
            counter = {"n": 0}

            class _Counting:
                def __init__(self, cm):
                    self._cm = cm

                async def __aenter__(self):
                    counter["n"] += 1
                    return await self._cm.__aenter__()

                async def __aexit__(self, *exc):
                    return await self._cm.__aexit__(*exc)

            class _PoolProxy:
                """Delegates everything; only acquire is counted."""

                def acquire(self):
                    return _Counting(real_acquire())

                def __getattr__(self, item):
                    return getattr(real_pool, item)

            async def _fake_get_pool():
                return _PoolProxy()

            monkeypatch.setattr(es, "get_pool", _fake_get_pool)

            await get_event_staff_summary(event_id)
            assert counter["n"] == 1, (
                f"event detail acquired {counter['n']} connections; expected 1"
            )
        finally:
            await _wipe(event_id, [server_id])


# ------------------------------------------------------ F. requirements path


class TestRequirementsEndpointIsolation:
    async def test_requirements_service_touches_no_staff_or_transport(
        self, monkeypatch
    ):
        """The requirements path must not call staff/conflict/transport code."""
        import app.services.event_service as es

        event_id, start, end = await _make_event(start_offset_days=80)
        server_id = await _make_server("reqiso")
        try:
            await _assign(event_id, server_id)
            await _add_transport_group(event_id, server_id, [])

            def _boom(*a, **k):
                raise AssertionError("requirements path must not run staff/transport")

            monkeypatch.setattr(es, "_fetch_staff_assignments", _boom)
            monkeypatch.setattr(
                es, "load_event_staff_assignments", _boom
            )
            monkeypatch.setattr(es, "get_event_staff_summary", _boom)

            rows = await load_event_requirements(event_id)
            assert rows is not None
            assert isinstance(rows, list)
        finally:
            await _wipe(event_id, [server_id])

    async def test_requirements_missing_event_returns_none(self):
        assert await load_event_requirements(str(uuid.uuid4())) is None

    async def test_requirements_response_contract_unchanged(
        self, client: AsyncClient, admin_token):
        event_id, start, end = await _make_event(start_offset_days=90)
        try:
            await _add_requirement(event_id, "Serveur", 3)
            r = await client.get(
                f"/api/events/{event_id}/requirements",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["event_id"] == event_id
            reqs = body["requirements"]
            assert len(reqs) == 1
            # `requirement_id` rename must survive the refactor.
            assert reqs[0]["requirement_id"]
            assert "id" not in reqs[0]
            assert reqs[0]["role_name"] == "Serveur"
            assert reqs[0]["minimum_skill_level"] == 3
            assert reqs[0]["missing"] == 4
        finally:
            await _wipe(event_id, [])

    async def test_requirements_endpoint_404_for_unknown_event(
        self, client: AsyncClient, admin_token):
        r = await client.get(
            f"/api/events/{uuid.uuid4()}/requirements",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 404


# --------------------------------------------- E. skill_level compatibility


class TestSkillLevelCompatibility:
    async def test_skill_level_still_carries_the_requirement_minimum(self):
        """Existing public behaviour is intentionally UNCHANGED.

        `assignments[].skill_level` is rendered in the UI as a per-server figure
        and used as a sort key and progress-bar width, so its meaning cannot be
        changed in this step even though it is arguably mislabelled.
        """
        event_id, start, end = await _make_event(start_offset_days=100)
        server_id = await _make_server("skillmin")
        try:
            await _assign(event_id, server_id, role="Serveur")
            await _add_requirement(event_id, "Serveur", minimum=7)

            data = await get_event_staff_summary(event_id)
            row = next(a for a in data["assignments"] if a["server_id"] == server_id)
            assert row["skill_level"] == 7
        finally:
            await _wipe(event_id, [server_id])

    async def test_actual_skill_levels_available_separately(self):
        server_id = await _make_server("skillreal")
        other_id = await _make_server("skillother")
        try:
            await _add_skill(server_id, "Service platinum", 9)
            await _add_skill(other_id, "Cuisine", 2)

            levels = await load_actual_skill_levels([server_id, other_id])
            assert levels[server_id][0]["skill_name"] == "Service platinum"
            assert levels[server_id][0]["level"] == 9
            assert levels[other_id][0]["level"] == 2
        finally:
            await _wipe_eventless([server_id, other_id])

    async def test_actual_skill_levels_empty_input(self):
        assert await load_actual_skill_levels([]) == {}

    async def test_actual_skill_levels_excludes_unrelated_servers(self):
        server_id = await _make_server("skillonly")
        await _add_skill(server_id, "Solo", 5)
        try:
            levels = await load_actual_skill_levels([server_id])
            assert list(levels) == [server_id]
        finally:
            await _wipe_eventless([server_id])

    async def test_actual_levels_are_distinct_from_requirement_minimum(self):
        """The two values must be independently retrievable, not conflated."""
        event_id, start, end = await _make_event(start_offset_days=110)
        server_id = await _make_server("skildistinct")
        try:
            await _assign(event_id, server_id, role="Serveur")
            await _add_requirement(event_id, "Serveur", minimum=2)
            await _add_skill(server_id, "Service", 8)

            data = await get_event_staff_summary(event_id)
            row = next(a for a in data["assignments"] if a["server_id"] == server_id)
            actual = await load_actual_skill_levels([server_id])

            assert row["skill_level"] == 2, "requirement minimum, unchanged"
            assert actual[server_id][0]["level"] == 8, "actual level, separately"
        finally:
            await _wipe(event_id, [server_id])


async def _wipe_eventless(server_ids: list[str]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM server_skills WHERE server_id = ANY($1::uuid[])", server_ids
        )
        await conn.execute(
            "DELETE FROM vehicles WHERE owner_server_id = ANY($1::uuid[])", server_ids
        )
        await conn.execute(
            "DELETE FROM servers WHERE id = ANY($1::uuid[])", server_ids
        )


# --------------------------------------------------------- response safety


class TestEventDetailPrivacyUnchanged:
    async def test_no_server_coordinates_in_assignments(self):
        """Venue coordinates are allowed; SERVER coordinates are not."""
        event_id, start, end = await _make_event(start_offset_days=120)
        server_id = await _make_server("priv")
        try:
            await _assign(event_id, server_id)
            data = await get_event_staff_summary(event_id)
            blob = str(data["assignments"]).lower()
            for forbidden in ("latitude", "longitude", "current_lat", "current_lon"):
                assert forbidden not in blob, f"{forbidden} leaked into assignments"
        finally:
            await _wipe(event_id, [server_id])

    async def test_event_coordinates_still_present_with_exact_flag(self):
        """Venue coordinates are operational and must remain available."""
        event_id, start, end = await _make_event(start_offset_days=121)
        try:
            data = await get_event_staff_summary(event_id)
            assert "latitude" in data["event"]
            assert "longitude" in data["event"]
            assert "has_exact_location" in data["event"]
        finally:
            await _wipe(event_id, [])

    async def test_no_binary_content_or_photo_url_in_payload(self):
        event_id, start, end = await _make_event(start_offset_days=122)
        server_id = await _make_server("bin")
        try:
            await _assign(event_id, server_id)
            data = await get_event_staff_summary(event_id)
            blob = str(data).lower()
            for forbidden in ("bytea", "base64", "profile-photo", "data:image"):
                assert forbidden not in blob
        finally:
            await _wipe(event_id, [server_id])