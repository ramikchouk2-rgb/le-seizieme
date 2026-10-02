"""Step 24C-D-9A: the server create/update response contract.

`POST /api/servers` and `PATCH /api/servers/{id}` returned HTTP 500 at HEAD.
Three independent causes, all in the response contract:

1. `create_server`/`update_server` returned `dict(row)` straight from an asyncpg
   `Record`, so `id` and `city_id` were `UUID` objects and `created_at`/
   `updated_at` were `datetime` -- while `ServerResponse` declares all four as
   `str`. FastAPI then raised a response-validation error.
2. `worker_type` was never returned at all, although `ServerResponse` requires
   the key. It lives in `server_profile`, not `servers`, so no RETURNING clause
   on the servers table could supply it.
3. `data.get("worker_type", "BALANCED")` could never reach its default:
   `ServerCreateRequest.model_dump()` always emits the key, so an omitted
   worker_type arrived as an explicit `None`, `.get` returned that `None`, and
   the `server_profile.worker_type` NOT NULL constraint rejected it.

These tests go through the real HTTP router. The router and `ServerResponse`
are NOT weakened or bypassed: a test that asserted success against a relaxed
model would have hidden exactly the defect this step fixes.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.database import get_pool
from app.models.servers import (
    DEFAULT_WORKER_TYPE,
    ServerResponse,
    VALID_WORKER_TYPES,
)
from app.services.server_service import load_server_detail


# ------------------------------------------------------------------- helpers


def _auth(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


async def _city_id() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return str(await conn.fetchval("SELECT id FROM cities LIMIT 1"))


def _payload(city_id: str, **overrides) -> dict:
    """A minimal valid create payload. Tests override one field at a time."""
    body = {
        "first_name": "Contrat",
        "last_name": "Tenue",
        "email": f"contract_{uuid.uuid4()}@example.org",
        "phone": "+21690000000",
        "gender": "MALE",
        "city_id": city_id,
        "years_experience": 3,
    }
    body.update(overrides)
    return body


async def _make_server(uniform_size: str | None = None, worker_type: str = "BALANCED"):
    """Insert a server and its profile directly, bypassing the API under test."""
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
            VALUES ($1, 'Existing', 'Server', '+21690000001', $2, 'MALE', $3, 7,
                    $4::server_uniform_size)
            """,
            server_id,
            f"existing_{server_id}@example.org",
            city_id,
            uniform_size,
        )
        await conn.execute(
            """
            INSERT INTO server_profile (
                server_id, speed_score, punctuality_score, presentation_score,
                communication_score, teamwork_score, discipline_score,
                endurance_score, worker_type
            ) VALUES ($1, 5, 5, 5, 5, 5, 5, 5, $2)
            """,
            server_id,
            worker_type,
        )
    return str(server_id)


async def _wipe(server_ids: list[str]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        for sid in server_ids:
            await conn.execute(
                "DELETE FROM event_staff WHERE server_id = $1::uuid", sid
            )
            await conn.execute(
                "DELETE FROM transport_passengers WHERE server_id = $1::uuid", sid
            )
            await conn.execute(
                "DELETE FROM server_files WHERE server_id = $1::uuid", sid
            )
            await conn.execute(
                "DELETE FROM server_skills WHERE server_id = $1::uuid", sid
            )
            await conn.execute(
                "DELETE FROM server_profile WHERE server_id = $1::uuid", sid
            )
            await conn.execute("DELETE FROM servers WHERE id = $1::uuid", sid)


async def _delete_created(client: AsyncClient, admin_token: str, server_id: str):
    """The API has no DELETE /servers/{id}, so created rows are removed directly."""
    await _wipe([server_id])


# ---------------------------------------------------------------- A. POST


class TestCreateEndpointWorks:
    async def test_post_with_a_complete_valid_payload(self, client: AsyncClient,
                                                      admin_token):
        payload = _payload(await _city_id())
        r = await client.post(
            "/api/servers", json=payload, headers=_auth(admin_token)
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            assert r.json()["first_name"] == "Contrat"
            assert r.json()["email"] == payload["email"]
            assert r.json()["years_experience"] == 3
            # And it really exists.
            assert (await load_server_detail(server_id))["id"] == server_id
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_post_with_uniform_size_l(self, client: AsyncClient, admin_token):
        r = await client.post(
            "/api/servers",
            json=_payload(await _city_id(), uniform_size="L"),
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            assert r.json()["uniform_size"] == "L"
            assert (await load_server_detail(server_id))["uniform_size"] == "L"
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_post_without_uniform_size_returns_null(self, client: AsyncClient,
                                                           admin_token):
        r = await client.post(
            "/api/servers", json=_payload(await _city_id()), headers=_auth(admin_token)
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            assert r.json()["uniform_size"] is None
            assert (await load_server_detail(server_id))["uniform_size"] is None
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_post_with_explicit_null_uniform_size(self, client: AsyncClient,
                                                        admin_token):
        r = await client.post(
            "/api/servers",
            json=_payload(await _city_id(), uniform_size=None),
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            assert r.json()["uniform_size"] is None
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_post_without_worker_type_defaults_to_balanced(
        self, client: AsyncClient, admin_token
    ):
        """Cause 3: the intended BALANCED fallback must actually apply."""
        assert DEFAULT_WORKER_TYPE == "BALANCED"
        r = await client.post(
            "/api/servers", json=_payload(await _city_id()), headers=_auth(admin_token)
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            assert r.json()["worker_type"] == "BALANCED"
            assert (await load_server_detail(server_id))["worker_type"] == "BALANCED"
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_post_with_explicit_null_worker_type_also_defaults(
        self, client: AsyncClient, admin_token
    ):
        """An explicit null is the same as omitted: no profile, no crash."""
        r = await client.post(
            "/api/servers",
            json=_payload(await _city_id(), worker_type=None),
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            assert r.json()["worker_type"] == "BALANCED"
        finally:
            await _delete_created(client, admin_token, server_id)

    @pytest.mark.parametrize("worker_type", VALID_WORKER_TYPES)
    async def test_post_with_explicit_valid_worker_type(self, client: AsyncClient,
                                                        admin_token, worker_type):
        r = await client.post(
            "/api/servers",
            json=_payload(await _city_id(), worker_type=worker_type),
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            assert r.json()["worker_type"] == worker_type
            assert (
                await load_server_detail(server_id)
            )["worker_type"] == worker_type
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_post_still_preserves_the_score_defaults(self, client: AsyncClient,
                                                          admin_token):
        """The profile-score defaults must be unaffected by the response fix.

        Read from `server_profile` directly: `load_server_detail` does not expose
        the scores at all, which is a separate pre-existing gap and not this
        step's concern.
        """
        r = await client.post(
            "/api/servers", json=_payload(await _city_id()), headers=_auth(admin_token)
        )
        assert r.status_code == 200, r.text
        server_id = r.json()["id"]
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                profile = await conn.fetchrow(
                    """
                    SELECT speed_score, punctuality_score, presentation_score,
                           communication_score, teamwork_score, discipline_score,
                           endurance_score, worker_type
                    FROM server_profile WHERE server_id = $1::uuid
                    """,
                    server_id,
                )
            assert profile is not None, "no profile row was created"
            for field in (
                "speed_score", "punctuality_score", "presentation_score",
                "communication_score", "teamwork_score", "discipline_score",
                "endurance_score",
            ):
                assert profile[field] == 5, f"{field} default changed"
            assert profile["worker_type"] == "BALANCED"
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_post_still_rejects_a_duplicate_email(self, client: AsyncClient,
                                                       admin_token):
        server_id = await _make_server()
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                email = await conn.fetchval(
                    "SELECT email FROM servers WHERE id = $1::uuid", server_id
                )
            r = await client.post(
                "/api/servers",
                json=_payload(await _city_id(), email=email),
                headers=_auth(admin_token),
            )
            assert r.status_code == 409
        finally:
            await _wipe([server_id])


# --------------------------------------------------------------- B. invalid


class TestInvalidValuesStillRejected:
    async def test_invalid_worker_type_is_rejected_with_422(
        self, client: AsyncClient, admin_token
    ):
        """An off-list worker type used to surface as a database 500."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            before = await conn.fetchval("SELECT count(*) FROM servers")
        r = await client.post(
            "/api/servers",
            json=_payload(await _city_id(), worker_type="SUPER_WORKER"),
            headers=_auth(admin_token),
        )
        assert r.status_code == 422, r.text
        async with pool.acquire() as conn:
            after = await conn.fetchval("SELECT count(*) FROM servers")
        assert after == before, "a rejected payload must not create a row"

    async def test_invalid_worker_type_on_patch_is_rejected_with_422(
        self, client: AsyncClient, admin_token
    ):
        server_id = await _make_server()
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"worker_type": "SUPER_WORKER"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 422, r.text
            detail = await load_server_detail(server_id)
            assert detail["worker_type"] == "BALANCED", "value must be untouched"
        finally:
            await _wipe([server_id])

    async def test_invalid_uniform_size_is_rejected_with_422(
        self, client: AsyncClient, admin_token
    ):
        pool = await get_pool()
        async with pool.acquire() as conn:
            before = await conn.fetchval("SELECT count(*) FROM servers")
        r = await client.post(
            "/api/servers",
            json=_payload(await _city_id(), uniform_size="GRAND"),
            headers=_auth(admin_token),
        )
        assert r.status_code == 422, r.text
        async with pool.acquire() as conn:
            after = await conn.fetchval("SELECT count(*) FROM servers")
        assert after == before

    async def test_invalid_uniform_size_on_patch_is_rejected_with_422(
        self, client: AsyncClient, admin_token
    ):
        server_id = await _make_server(uniform_size="L")
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"uniform_size": "GRAND"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 422, r.text
            assert (await load_server_detail(server_id))["uniform_size"] == "L"
        finally:
            await _wipe([server_id])


# --------------------------------------------------------------- C. PATCH


class TestUpdateEndpointWorks:
    async def test_patch_existing_server_returns_a_valid_response(
        self, client: AsyncClient, admin_token
    ):
        server_id = await _make_server()
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"first_name": "Renomme", "years_experience": 11},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["first_name"] == "Renomme"
            assert body["years_experience"] == 11
            detail = await load_server_detail(server_id)
            assert detail["first_name"] == "Renomme"
            assert detail["years_experience"] == 11
        finally:
            await _wipe([server_id])

    async def test_patch_with_uniform_size_l(self, client: AsyncClient, admin_token):
        server_id = await _make_server()
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"uniform_size": "L"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            assert r.json()["uniform_size"] == "L"
            assert (await load_server_detail(server_id))["uniform_size"] == "L"
        finally:
            await _wipe([server_id])

    async def test_patch_with_explicit_null_clears_uniform_size(
        self, client: AsyncClient, admin_token
    ):
        server_id = await _make_server(uniform_size="S")
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"uniform_size": None},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            assert r.json()["uniform_size"] is None
            assert (await load_server_detail(server_id))["uniform_size"] is None
        finally:
            await _wipe([server_id])

    async def test_patch_omitting_uniform_size_preserves_it(
        self, client: AsyncClient, admin_token
    ):
        """Absent is not null: an unrelated PATCH must not clear the size."""
        server_id = await _make_server(uniform_size="XXL")
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"last_name": "Autre"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            assert r.json()["uniform_size"] == "XXL"
            assert (await load_server_detail(server_id))["uniform_size"] == "XXL"
            assert (await load_server_detail(server_id))["last_name"] == "Autre"
        finally:
            await _wipe([server_id])

    async def test_patch_reports_the_stored_worker_type(self, client: AsyncClient,
                                                       admin_token):
        server_id = await _make_server(worker_type="HARD_WORKER")
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"years_experience": 4},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            # Untouched by the request, still reported.
            assert r.json()["worker_type"] == "HARD_WORKER"
        finally:
            await _wipe([server_id])

    async def test_patch_updating_worker_type_reports_the_new_value(
        self, client: AsyncClient, admin_token
    ):
        server_id = await _make_server(worker_type="HARD_WORKER")
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"worker_type": "SOFT_WORKER"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            assert r.json()["worker_type"] == "SOFT_WORKER"
            assert (
                await load_server_detail(server_id)
            )["worker_type"] == "SOFT_WORKER"
        finally:
            await _wipe([server_id])

    async def test_patch_with_an_empty_body_still_returns_a_valid_response(
        self, client: AsyncClient, admin_token
    ):
        """No field to change: the response must still satisfy the model."""
        server_id = await _make_server(uniform_size="M")
        try:
            r = await client.patch(
                f"/api/servers/{server_id}", json={}, headers=_auth(admin_token)
            )
            assert r.status_code == 200, r.text
            assert r.json()["uniform_size"] == "M"
            assert r.json()["worker_type"] == "BALANCED"
        finally:
            await _wipe([server_id])

    async def test_patch_unknown_server_is_still_404(self, client: AsyncClient,
                                                     admin_token):
        r = await client.patch(
            f"/api/servers/{uuid.uuid4()}",
            json={"first_name": "X"},
            headers=_auth(admin_token),
        )
        assert r.status_code == 404

    async def test_patch_can_deactivate_a_server(self, client: AsyncClient,
                                                 admin_token):
        server_id = await _make_server()
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"is_active": False},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            assert r.json()["is_active"] is False
        finally:
            await _wipe([server_id])


# --------------------------------------------- D. declared contract (L)


class TestResponseMatchesDeclaredContract:
    async def test_post_response_satisfies_the_declared_model(
        self, client: AsyncClient, admin_token
    ):
        r = await client.post(
            "/api/servers",
            json=_payload(await _city_id(), uniform_size="XL",
                          worker_type="SOFT_WORKER"),
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        server_id = body["id"]
        try:
            # FastAPI already enforced this, but asserting it directly documents
            # the contract rather than relying on the route not raising.
            ServerResponse(**body)
            assert set(body) == set(ServerResponse.model_fields), (
                "response keys drifted from the declared model"
            )
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_ids_and_timestamps_are_strings(self, client: AsyncClient,
                                                  admin_token):
        r = await client.post(
            "/api/servers", json=_payload(await _city_id()), headers=_auth(admin_token)
        )
        assert r.status_code == 200, r.text
        body = r.json()
        server_id = body["id"]
        try:
            for field in ("id", "city_id", "created_at", "updated_at"):
                assert isinstance(body[field], str), (
                    f"{field} must be a string, got {type(body[field]).__name__}"
                )
            uuid.UUID(body["id"])
            uuid.UUID(body["city_id"])
            # Parseable, and created_at is not later than updated_at.
            created = datetime.fromisoformat(body["created_at"])
            updated = datetime.fromisoformat(body["updated_at"])
            assert created <= updated
            assert body["is_active"] is True
        finally:
            await _delete_created(client, admin_token, server_id)

    async def test_patch_response_satisfies_the_declared_model(
        self, client: AsyncClient, admin_token
    ):
        server_id = await _make_server(uniform_size="L")
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"uniform_size": "XS"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            body = r.json()
            ServerResponse(**body)
            assert body["uniform_size"] == "XS"
        finally:
            await _wipe([server_id])

    async def test_authorization_is_unchanged(self, client: AsyncClient,
                                             admin_token, staff_token):
        """The fix must not widen access: writes stay Manager/Admin only."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = str(await conn.fetchval("SELECT id FROM cities LIMIT 1"))
        body = _payload(city_id, email=f"authz_{uuid.uuid4()}@example.org")
        assert (
            await client.post("/api/servers", json=body)
        ).status_code in (401, 403)
        assert (
            await client.post(
                "/api/servers", json=body, headers=_auth(staff_token)
            )
        ).status_code in (401, 403)

        server_id = await _make_server()
        try:
            r = await client.patch(
                f"/api/servers/{server_id}",
                json={"first_name": "Staff"},
                headers=_auth(staff_token),
            )
            assert r.status_code in (401, 403)
            assert (await load_server_detail(server_id))["first_name"] == "Existing"
        finally:
            await _wipe([server_id])


# ------------------------------------------------------- E. regressions (M)


class TestNoRegression:
    async def test_server_detail_is_unchanged(self, client: AsyncClient,
                                              admin_token):
        server_id = await _make_server(uniform_size="L", worker_type="HARD_WORKER")
        try:
            r = await client.get(f"/api/servers/{server_id}",
                                 headers=_auth(admin_token))
            assert r.status_code == 200, r.text
            body = r.json()
            for field in (
                "id", "first_name", "last_name", "gender", "city",
                "years_experience", "worker_type", "availability_status",
                "email", "phone", "location", "skills", "vehicle",
                "availability", "upcoming_events", "points", "uniform_size",
                "has_profile_photo", "profile_photo",
                "verified_attestation_count",
            ):
                assert field in body, f"lost detail field {field}"
            assert body["worker_type"] == "HARD_WORKER"
            assert body["uniform_size"] == "L"
        finally:
            await _wipe([server_id])

    async def test_server_list_is_unchanged(self, client: AsyncClient, admin_token):
        server_id = await _make_server(uniform_size="XL")
        try:
            r = await client.get("/api/servers?page_size=100",
                                 headers=_auth(admin_token))
            assert r.status_code == 200, r.text
            items = r.json()["items"]
            row = next(i for i in items if i["id"] == server_id)
            for field in (
                "id", "first_name", "last_name", "gender", "city",
                "years_experience", "worker_type", "availability_status",
                "main_skill", "main_skill_level", "location_verified",
                "monthly_points", "rank", "has_profile_photo",
                "verified_attestation_count", "uniform_size",
            ):
                assert field in row, f"lost list field {field}"
            assert row["uniform_size"] == "XL"
        finally:
            await _wipe([server_id])

    async def test_patching_one_server_leaves_others_untouched(
        self, client: AsyncClient, admin_token
    ):
        first = await _make_server(uniform_size="S")
        second = await _make_server(uniform_size="M")
        try:
            r = await client.patch(
                f"/api/servers/{first}",
                json={"uniform_size": "XXL"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            assert (await load_server_detail(first))["uniform_size"] == "XXL"
            assert (await load_server_detail(second))["uniform_size"] == "M"
        finally:
            await _wipe([first, second])

    async def test_event_detail_skill_level_is_untouched_by_this_fix(
        self, client: AsyncClient, admin_token
    ):
        """The fix must not disturb the D-9 skill semantics on event detail."""
        pool = await get_pool()
        event_id = uuid.uuid4()
        server_id = await _make_server(uniform_size="L")
        start = datetime(2030, 1, 1, 9, 0) + timedelta(days=60)
        try:
            async with pool.acquire() as conn:
                city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
                await conn.execute(
                    """
                    INSERT INTO events (
                        id, name, client_name, city_id, address, start_datetime,
                        end_datetime, guest_count, event_type, status
                    ) VALUES ($1, 'evt9a', 'Client', $2, 'Adr', $3, $4, 20,
                              'PRIVATE', 'CONFIRMED')
                    """,
                    event_id, city_id, start, start + timedelta(hours=3),
                )
                await conn.execute(
                    """
                    INSERT INTO event_requirements (
                        event_id, role_name, quantity, minimum_skill_level
                    ) VALUES ($1, 'Serveur', 2, 7)
                    """,
                    event_id,
                )
                await conn.execute(
                    """
                    INSERT INTO event_staff (
                        event_id, server_id, role, assignment_status, confirmed_at
                    ) VALUES ($1, $2, 'Serveur', 'CONFIRMED', NOW())
                    """,
                    event_id, server_id,
                )
            r = await client.get(f"/api/events/{event_id}", headers=_auth(admin_token))
            assert r.status_code == 200, r.text
            row = next(a for a in r.json()["assignments"]
                       if a["server_id"] == server_id)
            assert row["skill_level"] == 7, "requirement minimum must be unchanged"
        finally:
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM event_staff WHERE event_id = $1", event_id
                )
                await conn.execute(
                    "DELETE FROM event_requirements WHERE event_id = $1", event_id
                )
                await conn.execute("DELETE FROM events WHERE id = $1", event_id)
            await _wipe([server_id])
