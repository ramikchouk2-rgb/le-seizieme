"""Step 24C-D-9: server uniform size.

The business rules under test:

* The value set is closed. XS..XXXL, nothing else -- not "L", not "l", not
  "GRAND", not "L ". A free-text column would let all of those coexist and force
  a print sheet to guess how to group them, so the value is a PostgreSQL enum
  and an invalid value is refused by the database as well as by the API.
* NULL is a real, valid state meaning "not recorded". Existing servers have no
  measured size, and no default is invented for them, because a default would
  assert a size nobody recorded and make it indistinguishable from a real one.
* An explicit null on PATCH CLEARS the value; omitting the key leaves it alone.
* Nothing about staffing, requirement semantics, transport, attestations, photos
  or audit changes. `assignments[].skill_level` on the event detail still means
  the requirement minimum, which is asserted here so a regression is caught.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.database import get_pool
from app.models.servers import (
    ServerCreateRequest,
    ServerProfileResponse,
    ServerResponse,
    ServerUniformSize,
    ServerUpdateRequest,
)
from app.services.event_service import (
    get_event_print_data,
    get_event_staff_summary,
)
from app.services.server_service import (
    create_server,
    load_server_detail,
    load_server_list,
    update_server,
)

EXPECTED_SIZES = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]


# ------------------------------------------------------------------- helpers


async def _make_server(tag: str, uniform_size: str | None = None):
    """Insert a server directly, so tests can control the stored size exactly.

    A `server_profile` row is created too, mirroring what `create_server` does,
    so a PATCH that updates profile fields behaves the way it would in
    production rather than silently updating zero rows.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        server_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO servers (
                id, first_name, last_name, phone, email, gender, city_id,
                years_experience, uniform_size
            )
            VALUES ($1, $2, 'Tenue', '+21697000000', $3, 'MALE', $4, 4,
                    $5::server_uniform_size)
            """,
            server_id,
            tag[:1].upper() + tag[1:],
            f"uniform_{tag}_{server_id}@example.org",
            city_id,
            uniform_size,
        )
        await conn.execute(
            """
            INSERT INTO server_profile (
                server_id, speed_score, punctuality_score, presentation_score,
                communication_score, teamwork_score, discipline_score,
                endurance_score, worker_type
            ) VALUES ($1, 5, 5, 5, 5, 5, 5, 5, 'BALANCED')
            """,
            server_id,
        )
    return str(server_id)


async def _make_event(start_offset_days: int = 1):
    pool = await get_pool()
    event_id = uuid.uuid4()
    start = datetime(2030, 1, 1, 9, 0) + timedelta(days=start_offset_days)
    async with pool.acquire() as conn:
        city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        await conn.execute(
            """
            INSERT INTO events (
                id, name, client_name, city_id, address, latitude, longitude,
                start_datetime, end_datetime, guest_count, event_type, status
            )
            VALUES ($1, $2, 'Client Tenue', $3, 'Adresse', 36.8, 10.1, $4, $5,
                    40, 'PRIVATE', 'CONFIRMED')
            """,
            event_id,
            f"uniform_{event_id}",
            city_id,
            start,
            start + timedelta(hours=3),
        )
    return str(event_id)


async def _assign(event_id: str, server_id: str, role: str = "Serveur"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_staff (
                event_id, server_id, role, assignment_status, confirmed_at
            ) VALUES ($1, $2, $3, 'CONFIRMED', NOW())
            """,
            event_id,
            server_id,
            role,
        )


async def _add_requirement(event_id: str, role: str = "Serveur", minimum: int = 3):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_requirements (
                event_id, role_name, quantity, minimum_skill_level
            ) VALUES ($1, $2, 4, $3)
            """,
            event_id,
            role,
            minimum,
        )


async def _wipe(event_id: str | None, server_ids: list[str]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if event_id is not None:
            await conn.execute(
                "DELETE FROM transport_passengers WHERE transport_group_id IN "
                "(SELECT id FROM transport_groups WHERE event_id = $1)",
                event_id,
            )
            await conn.execute(
                "DELETE FROM transport_groups WHERE event_id = $1", event_id
            )
            await conn.execute("DELETE FROM event_staff WHERE event_id = $1", event_id)
            await conn.execute(
                "DELETE FROM event_requirements WHERE event_id = $1", event_id
            )
        await conn.execute(
            "DELETE FROM server_files WHERE server_id = ANY($1::uuid[])", server_ids
        )
        await conn.execute(
            "DELETE FROM server_skills WHERE server_id = ANY($1::uuid[])", server_ids
        )
        await conn.execute(
            "DELETE FROM vehicles WHERE owner_server_id = ANY($1::uuid[])", server_ids
        )
        await conn.execute("DELETE FROM server_profile WHERE server_id = ANY($1::uuid[])",
                           server_ids)
        await conn.execute("DELETE FROM servers WHERE id = ANY($1::uuid[])", server_ids)
        if event_id is not None:
            await conn.execute("DELETE FROM events WHERE id = $1", event_id)


# ------------------------------------------------------------------ A. enum


class TestUniformSizeEnum:
    def test_python_enum_has_exactly_the_seven_sizes(self):
        assert [s.value for s in ServerUniformSize] == EXPECTED_SIZES

    def test_enum_members_are_plain_strings(self):
        """A `str` enum keeps the API speaking plain strings."""
        assert ServerUniformSize.L == "L"
        assert ServerUniformSize.XXL.value == "XXL"

    async def test_database_enum_matches_the_python_enum(self):
        """The two definitions must not drift apart."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT enumlabel FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'server_uniform_size'
                ORDER BY e.enumsortorder
                """
            )
        assert [r["enumlabel"] for r in rows] == EXPECTED_SIZES

    async def test_enum_is_ordered_smallest_to_largest(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            ordered = await conn.fetchval(
                """
                SELECT 'XS'::server_uniform_size < 'XXXL'::server_uniform_size
                """
            )
        assert ordered is True


# -------------------------------------------------------------- B. nullable


class TestUniformSizeIsNullable:
    async def test_column_is_nullable_with_no_default(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            column = await conn.fetchrow(
                """
                SELECT is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'servers' AND column_name = 'uniform_size'
                """
            )
        assert column is not None
        assert column["is_nullable"] == "YES"
        # A default would assert a size nobody recorded.
        assert column["column_default"] is None

    async def test_null_is_accepted(self):
        server_id = await _make_server("nullable")
        try:
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] is None
        finally:
            await _wipe(None, [server_id])

    async def test_an_insert_that_omits_the_column_leaves_it_null(self):
        """There is no hidden default and no backfill trigger.

        Proved directly rather than by counting rows, so the assertion cannot be
        confused by data another test happened to create.
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
            server_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO servers (
                    id, first_name, last_name, phone, email, gender, city_id,
                    years_experience
                ) VALUES ($1, 'NoSize', 'Tenue', '+21691000000', $2, 'MALE', $3, 1)
                """,
                server_id,
                f"nosize_{server_id}@example.org",
                city_id,
            )
            try:
                value = await conn.fetchval(
                    "SELECT uniform_size FROM servers WHERE id = $1", server_id
                )
                assert value is None
                # And an unrelated UPDATE must not fill it in either.
                await conn.execute(
                    "UPDATE servers SET years_experience = 2 WHERE id = $1", server_id
                )
                value = await conn.fetchval(
                    "SELECT uniform_size FROM servers WHERE id = $1", server_id
                )
                assert value is None, "an unrelated update must not set a size"
            finally:
                await conn.execute(
                    "DELETE FROM servers WHERE id = $1", server_id
                )

    async def test_model_allows_none(self):
        payload = ServerCreateRequest(
            first_name="A",
            last_name="B",
            email="none@example.org",
            phone="+21600000000",
            gender="MALE",
            city_id="00000000-0000-0000-0000-000000000001",
        )
        assert payload.uniform_size is None


# ----------------------------------------------------------------- C. create


class TestCreateWithUniformSize:
    """Create is exercised at the SERVICE layer, not through POST /api/servers.

    That endpoint is broken independently of this step: `create_server` returns
    raw UUID/datetime values and never selects `worker_type`, while
    `ServerResponse` requires `worker_type` and str-typed ids and timestamps. A
    test asserting a 200 here would be pinning a pre-existing 500, so the service
    contract is verified directly instead. See the step's final report.
    """

    async def _create(self, size: str | None) -> str:
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        payload = ServerCreateRequest(
            first_name="Cree",
            last_name="Tenue",
            email=f"create_{uuid.uuid4()}@example.org",
            phone="+21696000000",
            gender="FEMALE",
            city_id=str(city_id),
            uniform_size=size,
            worker_type="BALANCED",
        )
        result = await create_server(payload.model_dump())
        return str(result["id"])

    async def test_create_with_size(self):
        server_id = await self._create("XL")
        try:
            assert (await load_server_detail(server_id))["uniform_size"] == "XL"
        finally:
            await _wipe(None, [server_id])

    async def test_create_without_size(self):
        server_id = await self._create(None)
        try:
            assert (await load_server_detail(server_id))["uniform_size"] is None
        finally:
            await _wipe(None, [server_id])

    async def test_create_returns_the_size_in_its_result(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        payload = ServerCreateRequest(
            first_name="Retour",
            last_name="Tenue",
            email=f"retour_{uuid.uuid4()}@example.org",
            phone="+21693000000",
            gender="MALE",
            city_id=str(city_id),
            uniform_size="XXXL",
            worker_type="BALANCED",
        )
        result = await create_server(payload.model_dump())
        server_id = str(result["id"])
        try:
            assert result["uniform_size"] == "XXXL"
            # The declared model carries the field, so the value is part of the
            # contract rather than an accident of the query.
            assert "uniform_size" in ServerResponse.model_fields
        finally:
            await _wipe(None, [server_id])

    async def test_every_valid_size_round_trips(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        for size in EXPECTED_SIZES:
            payload = ServerCreateRequest(
                first_name="Tous",
                last_name="Tailles",
                email=f"all_{size}_{uuid.uuid4()}@example.org",
                phone="+21692000000",
                gender="MALE",
                city_id=str(city_id),
                uniform_size=size,
                worker_type="BALANCED",
            )
            result = await create_server(payload.model_dump())
            server_id = str(result["id"])
            try:
                detail = await load_server_detail(server_id)
                assert detail["uniform_size"] == size
            finally:
                await _wipe(None, [server_id])


# ----------------------------------------------------------------- D. update


class TestUpdateUniformSize:
    async def test_update_sets_a_size(self):
        server_id = await _make_server("updset")
        try:
            payload = ServerUpdateRequest(uniform_size="XXL")
            result = await update_server(
                server_id, payload.model_dump(exclude_unset=True)
            )
            assert result["uniform_size"] == "XXL"
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] == "XXL"
        finally:
            await _wipe(None, [server_id])

    async def test_update_replaces_an_existing_size(self):
        server_id = await _make_server("updrepl", uniform_size="S")
        try:
            payload = ServerUpdateRequest(uniform_size="L")
            await update_server(server_id, payload.model_dump(exclude_unset=True))
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] == "L"
        finally:
            await _wipe(None, [server_id])

    async def test_invalid_value_is_rejected_by_patch_validation(self):
        """PATCH refuses an off-list value before touching the row."""
        from pydantic import ValidationError

        server_id = await _make_server("patchbad", uniform_size="L")
        try:
            with pytest.raises(ValidationError):
                ServerUpdateRequest(uniform_size="GRAND")
            # The stored value is untouched.
            assert (await load_server_detail(server_id))["uniform_size"] == "L"
        finally:
            await _wipe(None, [server_id])

    async def test_omitting_the_key_leaves_the_size_untouched(self):
        """Absent is not the same as null: an unrelated PATCH must not clear it."""
        server_id = await _make_server("updkeep", uniform_size="M")
        try:
            payload = ServerUpdateRequest(first_name="Renomme")
            await update_server(server_id, payload.model_dump(exclude_unset=True))
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] == "M"
            assert detail["first_name"] == "Renomme"
        finally:
            await _wipe(None, [server_id])

    async def test_other_existing_patch_behaviour_is_unchanged(self):
        """The explicit-null handling must not disturb the other fields."""
        server_id = await _make_server("updother", uniform_size="L")
        try:
            payload = ServerUpdateRequest(
                years_experience=9, worker_type="SOFT_WORKER", is_active=False
            )
            await update_server(server_id, payload.model_dump(exclude_unset=True))
            detail = await load_server_detail(server_id)
            assert detail["years_experience"] == 9
            assert detail["worker_type"] == "SOFT_WORKER"
            assert detail["uniform_size"] == "L"
        finally:
            await _wipe(None, [server_id])


# ------------------------------------------------------ E. clear to null


class TestUniformSizeCanBeCleared:
    async def test_explicit_null_clears_the_size(self):
        server_id = await _make_server("clearme", uniform_size="XL")
        try:
            payload = ServerUpdateRequest(uniform_size=None)
            data = payload.model_dump(exclude_unset=True)
            # The key must be present with a null value: that is what makes an
            # explicit clear different from an omitted field.
            assert "uniform_size" in data and data["uniform_size"] is None
            await update_server(server_id, data)
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] is None
        finally:
            await _wipe(None, [server_id])

    async def test_explicit_null_clears_through_the_patch_model(self):
        """The same clear path the router takes, minus the pre-existing 500."""
        server_id = await _make_server("clearpatch", uniform_size="S")
        try:
            data = ServerUpdateRequest(uniform_size=None).model_dump(exclude_unset=True)
            await update_server(server_id, data)
            assert (await load_server_detail(server_id))["uniform_size"] is None
        finally:
            await _wipe(None, [server_id])

    async def test_a_size_can_be_set_again_after_clearing(self):
        server_id = await _make_server("resetsize", uniform_size="XS")
        try:
            await update_server(
                server_id,
                ServerUpdateRequest(uniform_size=None).model_dump(exclude_unset=True),
            )
            assert (await load_server_detail(server_id))["uniform_size"] is None
            await update_server(
                server_id,
                ServerUpdateRequest(uniform_size="XXL").model_dump(exclude_unset=True),
            )
            assert (await load_server_detail(server_id))["uniform_size"] == "XXL"
        finally:
            await _wipe(None, [server_id])

    async def test_clearing_an_already_null_size_is_harmless(self):
        server_id = await _make_server("clearnull")
        try:
            result = await update_server(
                server_id,
                ServerUpdateRequest(uniform_size=None).model_dump(exclude_unset=True),
            )
            assert result["uniform_size"] is None
        finally:
            await _wipe(None, [server_id])


# --------------------------------------------------------- F. detail / list


class TestUniformSizeInReads:
    async def test_server_detail_exposes_the_size(self):
        server_id = await _make_server("detail", uniform_size="L")
        try:
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] == "L"
            # The declared response model must accept it.
            model = ServerProfileResponse(**detail)
            assert model.uniform_size == ServerUniformSize.L
        finally:
            await _wipe(None, [server_id])

    async def test_server_detail_exposes_null(self):
        server_id = await _make_server("detailnull")
        try:
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] is None
            model = ServerProfileResponse(**detail)
            assert model.uniform_size is None
        finally:
            await _wipe(None, [server_id])

    async def test_detail_endpoint_exposes_the_size(
        self, client: AsyncClient, admin_token
    ):
        server_id = await _make_server("detailapi", uniform_size="XXL")
        try:
            r = await client.get(
                f"/api/servers/{server_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text
            assert r.json()["uniform_size"] == "XXL"
        finally:
            await _wipe(None, [server_id])

    async def test_server_list_exposes_the_size(self):
        server_id = await _make_server("listitem", uniform_size="M")
        try:
            rows, _ = await load_server_list(
                search=None, city=None, gender=None, availability=None,
                worker_type=None, has_vehicle=None, can_transport=None,
                location_verified=None, skill=None, min_experience=None,
                max_experience=None, sort_by="first_name", sort_order="asc",
                page=1, page_size=100,
            )
            row = next(r for r in rows if r["id"] == server_id)
            assert row["uniform_size"] == "M"
        finally:
            await _wipe(None, [server_id])

    async def test_server_list_reports_null_rather_than_empty_string(self):
        """Unlike worker_type, a missing size must not become ""."""
        server_id = await _make_server("listnull")
        try:
            rows, _ = await load_server_list(
                search=None, city=None, gender=None, availability=None,
                worker_type=None, has_vehicle=None, can_transport=None,
                location_verified=None, skill=None, min_experience=None,
                max_experience=None, sort_by="first_name", sort_order="asc",
                page=1, page_size=100,
            )
            row = next(r for r in rows if r["id"] == server_id)
            assert row["uniform_size"] is None
        finally:
            await _wipe(None, [server_id])

    async def test_response_model_declares_the_field(self):
        assert "uniform_size" in ServerResponse.model_fields
        assert "uniform_size" in ServerProfileResponse.model_fields


# ---------------------------------------------------------- G. print data


class TestUniformSizeInPrintData:
    async def test_print_data_returns_the_size(self):
        event_id = await _make_event(start_offset_days=10)
        server_id = await _make_server("printsize", uniform_size="L")
        try:
            await _assign(event_id, server_id)
            data = await get_event_print_data(event_id)
            assert data["assignments"][0]["uniform_size"] == "L"
        finally:
            await _wipe(event_id, [server_id])

    async def test_print_data_returns_null_when_unrecorded(self):
        event_id = await _make_event(start_offset_days=11)
        server_id = await _make_server("printnull")
        try:
            await _assign(event_id, server_id)
            data = await get_event_print_data(event_id)
            assert data["assignments"][0]["uniform_size"] is None
        finally:
            await _wipe(event_id, [server_id])

    async def test_print_data_carries_a_real_size_per_server(self):
        event_id = await _make_event(start_offset_days=12)
        big = await _make_server("printbig", uniform_size="XXL")
        small = await _make_server("printsmall", uniform_size="XS")
        try:
            await _assign(event_id, big)
            await _assign(event_id, small)
            data = await get_event_print_data(event_id)
            sizes = {
                a["server_id"]: a["uniform_size"] for a in data["assignments"]
            }
            assert sizes[big] == "XXL"
            assert sizes[small] == "XS"
        finally:
            await _wipe(event_id, [big, small])

    async def test_print_data_endpoint_exposes_the_size(
        self, client: AsyncClient, admin_token
    ):
        event_id = await _make_event(start_offset_days=13)
        server_id = await _make_server("printapi", uniform_size="M")
        try:
            await _assign(event_id, server_id)
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text
            assert r.json()["assignments"][0]["uniform_size"] == "M"
        finally:
            await _wipe(event_id, [server_id])

    async def test_print_data_adds_no_other_server_data(self):
        """The size must not drag extra server fields into the contract."""
        event_id = await _make_event(start_offset_days=14)
        server_id = await _make_server("printfields", uniform_size="L")
        try:
            await _assign(event_id, server_id)
            data = await get_event_print_data(event_id)
            row = data["assignments"][0]
            assert set(row) == {
                "server_id", "first_name", "last_name", "gender", "city",
                "years_experience", "role", "assignment_status", "assigned_at",
                "confirmed_at", "required_minimum_skill_level", "score",
                "uniform_size", "profile_photo_available", "actual_skills",
                "verified_attestations",
            }
            for forbidden in ("phone", "email", "is_active", "worker_type"):
                assert forbidden not in row, f"{forbidden} leaked into print data"
        finally:
            await _wipe(event_id, [server_id])


# --------------------------------------------------- H. invalid rejection


class TestInvalidUniformSizeRejected:
    @pytest.mark.parametrize("bad", ["GRAND", "l", "XXS", "4XL", "", "M ", "MEDIUM"])
    def test_model_rejects_off_list_values(self, bad):
        with pytest.raises(Exception):
            ServerCreateRequest(
                first_name="A",
                last_name="B",
                email="bad@example.org",
                phone="+21600000000",
                gender="MALE",
                city_id="00000000-0000-0000-0000-000000000001",
                uniform_size=bad,
            )

    def test_model_rejects_off_list_on_update(self):
        with pytest.raises(Exception):
            ServerUpdateRequest(uniform_size="GRAND")

    def test_model_accepts_every_valid_size(self):
        for size in EXPECTED_SIZES:
            assert ServerUpdateRequest(uniform_size=size).uniform_size == size

    def test_model_still_accepts_null(self):
        assert ServerUpdateRequest(uniform_size=None).uniform_size is None

    async def test_api_rejects_an_invalid_value_before_any_write(
        self, client: AsyncClient, admin_token
    ):
        """422, not a silent coercion to a near-miss string.

        Rejection happens during validation, before the service is reached, so
        this is asserted even though the success path of this endpoint is
        separately broken for unrelated reasons.
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
            before = await conn.fetchval("SELECT count(*) FROM servers")
        r = await client.post(
            "/api/servers",
            json={
                "first_name": "Api",
                "last_name": "Tenue",
                "email": f"invalid_{uuid.uuid4()}@example.org",
                "phone": "+21694000000",
                "gender": "MALE",
                "city_id": str(city_id),
                "uniform_size": "GRAND",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 422, r.text
        async with pool.acquire() as conn:
            after = await conn.fetchval("SELECT count(*) FROM servers")
        assert after == before, "an invalid value must not create a row"

    async def test_database_rejects_an_invalid_value_directly(self):
        """Defence in depth: even a bypassing caller cannot store free text."""
        server_id = await _make_server("dbguard")
        try:
            pool = await get_pool()
            with pytest.raises(Exception):
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE servers SET uniform_size = 'GRAND' WHERE id = $1::uuid",
                        server_id,
                    )
            detail = await load_server_detail(server_id)
            assert detail["uniform_size"] is None
        finally:
            await _wipe(None, [server_id])

    async def test_lowercase_is_not_coerced(self):
        """'l' must be refused, not folded up to 'L'."""
        server_id = await _make_server("lower")
        try:
            pool = await get_pool()
            with pytest.raises(Exception):
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE servers SET uniform_size = 'l' WHERE id = $1::uuid",
                        server_id,
                    )
        finally:
            await _wipe(None, [server_id])


# --------------------------------------------------------- I. regressions


class TestNoRegressionToExistingContracts:
    async def test_event_detail_skill_level_is_unchanged(self):
        """The requirement minimum keeps its existing meaning."""
        event_id = await _make_event(start_offset_days=20)
        server_id = await _make_server("regress", uniform_size="L")
        try:
            await _add_requirement(event_id, "Serveur", minimum=7)
            await _assign(event_id, server_id, role="Serveur")
            detail = await get_event_staff_summary(event_id)
            row = next(
                a for a in detail["assignments"] if a["server_id"] == server_id
            )
            # Still the requirement minimum, not the server's level and not the
            # uniform size.
            assert row["skill_level"] == 7
        finally:
            await _wipe(event_id, [server_id])

    async def test_event_detail_does_not_expose_uniform_size(self):
        """This step adds the size to print-data only, not to the old contract."""
        event_id = await _make_event(start_offset_days=21)
        server_id = await _make_server("regress2", uniform_size="L")
        try:
            await _assign(event_id, server_id)
            detail = await get_event_staff_summary(event_id)
            row = next(
                a for a in detail["assignments"] if a["server_id"] == server_id
            )
            assert "uniform_size" not in row
        finally:
            await _wipe(event_id, [server_id])

    async def test_requirement_minimum_and_uniform_size_stay_separate(self):
        """A large uniform must not be mistaken for a high skill requirement."""
        event_id = await _make_event(start_offset_days=22)
        server_id = await _make_server("regress3", uniform_size="XXXL")
        try:
            await _add_requirement(event_id, "Serveur", minimum=2)
            await _assign(event_id, server_id, role="Serveur")
            data = await get_event_print_data(event_id)
            assert data["requirements"][0]["required_minimum_skill_level"] == 2
            assert data["assignments"][0]["uniform_size"] == "XXXL"
            assert data["assignments"][0]["actual_skills"] == []
        finally:
            await _wipe(event_id, [server_id])

    async def test_existing_server_fields_are_untouched(self):
        server_id = await _make_server("regress4", uniform_size="L")
        try:
            detail = await load_server_detail(server_id)
            for field in (
                "id", "first_name", "last_name", "gender", "city",
                "years_experience", "worker_type", "availability_status",
                "email", "phone", "location", "skills", "availability",
                "upcoming_events", "points", "has_profile_photo",
                "profile_photo", "verified_attestation_count",
            ):
                assert field in detail, f"lost existing detail field {field}"
        finally:
            await _wipe(None, [server_id])

    async def test_staffing_scoring_is_unaffected(self):
        """The scoring function must know nothing about a uniform size."""
        import inspect

        from app.utils.selection_utils import compute_candidate_score

        source = inspect.getsource(compute_candidate_score)
        assert "uniform_size" not in source

    async def test_print_path_does_not_score_candidates(self):
        """The print-data path carries a size but computes no score."""
        import ast
        import inspect

        import app.services.event_service as es

        tree = ast.parse(inspect.getsource(es.get_event_print_data))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "compute_candidate_score" not in called
