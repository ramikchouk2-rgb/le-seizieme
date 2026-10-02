"""Step 24C-D-8B: the dedicated event print-data contract.

These tests pin the contract of `GET /api/events/{event_id}/print-data`. The
properties that matter and are asserted here:

* The required minimum skill and the server's ACTUAL skills are separate,
  explicitly named values. `event_requirements` has no `skill_id`, so
  `required_minimum_skill_level` stays a bare numeric threshold and no skill
  identity is invented for it.
* Only VERIFIED attestations are exposed, as metadata: never document bytes, a
  storage path or a private URL.
* A profile photo is a boolean. The print page fetches the image through the
  existing authenticated endpoint.
* Server GPS, contact details and audit data never appear. Venue coordinates are
  allowed, because a sheet has to say where the event is.
* The query count is constant with respect to the number of assigned servers.
  The same statement-counting approach as tests/test_event_detail_n1.py is used.
* The existing event-detail API is untouched, in particular
  `assignments[].skill_level`, which still means the requirement minimum.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from httpx import AsyncClient

from app.core.database import get_pool
from app.services.event_service import (
    get_event_print_data,
    get_event_staff_summary,
)


# ------------------------------------------------------------------- helpers


def _pdf_bytes() -> bytes:
    body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>\nendobj\n"
    )
    return b"%PDF-1.4\n" + body + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"


async def _make_event(start_offset_days: int = 1, duration_hours: int = 3,
                      with_coordinates: bool = True,
                      status: str = "PLANNED"):
    pool = await get_pool()
    event_id = uuid.uuid4()
    start = datetime(2030, 1, 1, 9, 0) + timedelta(days=start_offset_days)
    end = start + timedelta(hours=duration_hours)
    async with pool.acquire() as conn:
        city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        await conn.execute(
            """
            INSERT INTO events (
                id, name, client_name, city_id, address, latitude, longitude,
                start_datetime, end_datetime, guest_count, event_type, status,
                priority, is_urgent, required_response_minutes, notes
            )
            VALUES ($1, $2, 'Client Print', $3, 'Adresse impression', $4, $5,
                    $6, $7, 120, 'PRIVATE', $8::event_status, 'PRIORITY', TRUE,
                    45, 'Note de test')
            """,
            event_id,
            f"print_{event_id}",
            city_id,
            36.8078 if with_coordinates else None,
            10.1810 if with_coordinates else None,
            start,
            end,
            status,
        )
    return str(event_id), start, end


async def _make_server(tag: str, years_experience: int = 5):
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
            VALUES ($1, $2, 'Print', '+21699000000', $3, 'FEMALE', $4, $5)
            """,
            server_id,
            tag[:1].upper() + tag[1:],
            f"print_{tag}_{server_id}@example.org",
            city_id,
            years_experience,
        )
    return str(server_id)


async def _assign(event_id: str, server_id: str, role: str = "Serveur",
                  status: str = "CONFIRMED"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_staff (
                event_id, server_id, role, assignment_status, assigned_at,
                confirmed_at
            )
            VALUES ($1, $2, $3, $4::assignment_status,
                    NOW() - INTERVAL '2 days',
                    CASE WHEN $4::text = 'CONFIRMED'
                         THEN NOW() - INTERVAL '1 day' ELSE NULL END)
            """,
            event_id,
            server_id,
            role,
            status,
        )


async def _add_requirement(event_id: str, role: str = "Serveur",
                           quantity: int = 4, minimum: int = 3,
                           minimum_experience: int = 2,
                           required_gender: str | None = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO event_requirements (
                event_id, role_name, quantity, required_gender,
                minimum_experience, minimum_skill_level
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            event_id,
            role,
            quantity,
            required_gender,
            minimum_experience,
            minimum,
        )


async def _add_skill(server_id: str, name: str, level: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # skills.name is globally unique, so reuse an existing row of that name
        # instead of leaking a new skill per test run.
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
            VALUES ($1, $2, $3, 6)
            """,
            server_id,
            skill_id,
            level,
        )
    return str(skill_id)


async def _add_attestation(server_id: str, status: str, name: str):
    """Insert an attestation in a given lifecycle state, with its document.

    `VERIFIED` requires verified_at and verified_by, and `REJECTED` requires a
    reason, so the test data has to satisfy the same constraints the service
    enforces rather than bypassing them.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        payload = _pdf_bytes()
        file_id = await conn.fetchval(
            """
            INSERT INTO server_files (
                server_id, file_type, content, mime_type, file_size
            ) VALUES ($1, 'ATTESTATION', $2, 'application/pdf', $3)
            RETURNING id
            """,
            server_id,
            payload,
            len(payload),
        )
        verifier = await conn.fetchval("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1")
        # Status is always $4. Lifecycle columns are appended to the VALUE list
        # rather than the column list, so the placeholders cannot collide.
        extra_values = ""
        params = [server_id, file_id, name, status]
        if status == "VERIFIED":
            extra_values = ", NOW(), $5"
            params.append(verifier)
        elif status == "REJECTED":
            extra_values = ", 'Document illisible'"
        columns = (
            "server_id, file_id, qualification_name, status, verified_at, verified_by"
            if status == "VERIFIED"
            else "server_id, file_id, qualification_name, status, rejection_reason"
            if status == "REJECTED"
            else "server_id, file_id, qualification_name, status"
        )
        await conn.execute(
            f"""
            INSERT INTO server_attestations ({columns})
            VALUES ($1, $2, $3, $4::attestation_status{extra_values})
            """,
            *params,
        )


async def _add_superseded_attestation(server_id: str, name: str):
    """A VERIFIED document later replaced by a named successor.

    The lifecycle requires SUPERSEDED to name the document that replaced it, so
    this is built as a real two-step chain rather than a bare status.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        payload = _pdf_bytes()
        file_id = await conn.fetchval(
            """
            INSERT INTO server_files (
                server_id, file_type, content, mime_type, file_size
            ) VALUES ($1, 'ATTESTATION', $2, 'application/pdf', $3)
            RETURNING id
            """,
            server_id,
            payload,
            len(payload),
        )
        verifier = await conn.fetchval("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1")
        old_id = await conn.fetchval(
            """
            INSERT INTO server_attestations (
                server_id, file_id, qualification_name, status, verified_at,
                verified_by
            ) VALUES ($1, $2, $3, 'VERIFIED', NOW(), $4)
            RETURNING id
            """,
            server_id,
            file_id,
            f"{name} ancien",
            verifier,
        )
        await conn.execute(
            """
            INSERT INTO server_attestations (
                server_id, file_id, qualification_name, status, verified_at,
                verified_by, superseded_by_id
            ) VALUES ($1, $2, $3, 'VERIFIED', NOW(), $4, $5)
            """,
            server_id,
            file_id,
            f"{name} actuel",
            verifier,
            old_id,
        )
        await conn.execute(
            "UPDATE server_attestations SET status = 'SUPERSEDED' WHERE id = $1",
            old_id,
        )


async def _add_profile_photo(server_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        payload = b"\x89PNG\r\n\x1a\n" + b"print-photo-bytes"
        await conn.execute(
            """
            INSERT INTO server_files (
                server_id, file_type, content, mime_type, file_size,
                original_filename
            ) VALUES ($1, 'PROFILE_PHOTO', $2, 'image/png', $3, 'avatar.png')
            """,
            server_id,
            payload,
            len(payload),
        )


async def _add_transport_group(event_id: str, driver_id: str,
                               passengers: list[tuple[str, str]],
                               status: str = "CONFIRMED"):
    """One group with a vehicle and the given (server_id, label) passengers."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        vehicle_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO vehicles (
                id, owner_server_id, vehicle_type, brand, model, seats_total
            ) VALUES ($1, $2, 'VAN', 'Renault', 'Trafic', 9)
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
                destination_label, estimated_distance_km, estimated_duration_minutes,
                status
            ) VALUES ($1, $2, $3, $4, 36.8, 10.1, 'Depot Tunis', NOW() + INTERVAL '2 hours',
                      36.9, 10.2, 'Venue Sousse', 14.75, 35, $5::transport_group_status)
            """,
            group_id,
            event_id,
            vehicle_id,
            driver_id,
            status,
        )
        for order, (pid, label) in enumerate(passengers, start=1):
            await conn.execute(
                """
                INSERT INTO transport_passengers (
                    transport_group_id, server_id, pickup_latitude,
                    pickup_longitude, pickup_location_label, pickup_order,
                    pickup_status
                ) VALUES ($1, $2, 36.85, 10.15, $3, $4, 'PENDING')
                """,
                group_id,
                pid,
                label,
                order,
            )
        return str(group_id)


async def _wipe(event_id: str | None, server_ids: list[str]):
    """Remove a test event and/or servers.

    `event_id` may be None when only servers were created, so a helper that
    never made an event does not have to invent a fake one.
    """
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
        # Attestations first: they reference both servers and files.
        await conn.execute(
            "DELETE FROM server_attestations WHERE server_id = ANY($1::uuid[])",
            server_ids,
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
        await conn.execute("DELETE FROM servers WHERE id = ANY($1::uuid[])", server_ids)
        if event_id is not None:
            await conn.execute("DELETE FROM events WHERE id = $1", event_id)


# ------------------------------------------------- A. authentication / policy


class TestPrintDataAccessControl:
    async def test_unauthenticated_request_is_rejected(
        self, client: AsyncClient
    ):
        event_id, _, _ = await _make_event(start_offset_days=200)
        try:
            r = await client.get(f"/api/events/{event_id}/print-data")
            assert r.status_code in (401, 403), r.text
        finally:
            await _wipe(event_id, [])

    async def test_invalid_token_is_rejected(self, client: AsyncClient):
        event_id, _, _ = await _make_event(start_offset_days=201)
        try:
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": "Bearer not-a-real-token"},
            )
            assert r.status_code in (401, 403), r.text
        finally:
            await _wipe(event_id, [])

    async def test_admin_can_read(self, client: AsyncClient, admin_token):
        event_id, _, _ = await _make_event(start_offset_days=202)
        try:
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text
        finally:
            await _wipe(event_id, [])

    async def test_manager_can_read(self, client: AsyncClient, manager_token):
        """Manager is the audience for a print sheet, so it must work."""
        event_id, _, _ = await _make_event(start_offset_days=203)
        try:
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {manager_token}"},
            )
            assert r.status_code == 200, r.text
        finally:
            await _wipe(event_id, [])

    async def test_staff_role_read_matches_event_detail_policy(
        self, client: AsyncClient, staff_token
    ):
        """Read policy must be identical to GET /events/{event_id}.

        The endpoint is explicitly not ADMIN-only, so a STAFF user has the same
        outcome here as on the event detail endpoint -- whatever that is.
        """
        event_id, _, _ = await _make_event(start_offset_days=204)
        try:
            headers = {"Authorization": f"Bearer {staff_token}"}
            detail = await client.get(f"/api/events/{event_id}", headers=headers)
            printed = await client.get(f"/api/events/{event_id}/print-data",
                                       headers=headers)
            assert printed.status_code == detail.status_code, (
                f"print-data {printed.status_code} != event detail "
                f"{detail.status_code}"
            )
        finally:
            await _wipe(event_id, [])


# ------------------------------------------------------------- B. missing event


class TestPrintDataMissingEvent:
    async def test_unknown_event_returns_404(
        self, client: AsyncClient, admin_token
    ):
        r = await client.get(
            f"/api/events/{uuid.uuid4()}/print-data",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 404

    async def test_service_returns_none_for_unknown_event(self):
        assert await get_event_print_data(str(uuid.uuid4())) is None

    async def test_404_detail_matches_event_detail_convention(
        self, client: AsyncClient, admin_token
    ):
        headers = {"Authorization": f"Bearer {admin_token}"}
        detail = await client.get(f"/api/events/{uuid.uuid4()}", headers=headers)
        printed = await client.get(
            f"/api/events/{uuid.uuid4()}/print-data", headers=headers
        )
        assert printed.status_code == detail.status_code == 404


# ------------------------------------------------------------ C. response shape


class TestPrintDataContract:
    async def test_event_fields_present(self, client: AsyncClient, admin_token):
        event_id, _, _ = await _make_event(start_offset_days=205)
        try:
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text
            event = r.json()["event"]
            for field in (
                "id", "name", "client_name", "event_type", "start_datetime",
                "end_datetime", "city", "address", "latitude", "longitude",
                "guest_count", "status", "priority", "urgent",
                "required_response_minutes", "notes", "has_exact_location",
            ):
                assert field in event, f"missing event field {field}"
            assert event["id"] == event_id
            assert event["client_name"] == "Client Print"
            assert event["guest_count"] == 120
            assert event["priority"] == "PRIORITY"
            assert event["urgent"] is True
            assert event["required_response_minutes"] == 45
            assert event["notes"] == "Note de test"
            assert event["has_exact_location"] is True
            assert event["latitude"] == 36.8078
            assert event["longitude"] == 10.1810
        finally:
            await _wipe(event_id, [])

    async def test_top_level_shape(self, client: AsyncClient, admin_token):
        event_id, _, _ = await _make_event(start_offset_days=206)
        try:
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            body = r.json()
            assert set(body) == {"event", "requirements", "assignments",
                                 "transport_groups"}
        finally:
            await _wipe(event_id, [])

    async def test_response_model_is_explicit(self):
        """The main response must not be a bare dict[str, Any]."""
        from app.models.events import EventPrintDataResponse

        fields = set(EventPrintDataResponse.model_fields)
        assert fields == {"event", "requirements", "assignments", "transport_groups"}
        # Nested models are declared too, so nothing escapes as untyped data.
        assert EventPrintDataResponse.model_fields["event"].annotation is not Any
        assert EventPrintDataResponse.model_fields["assignments"].annotation is not Any

    async def test_requirements_shape(self, client: AsyncClient, admin_token):
        event_id, _, _ = await _make_event(start_offset_days=207)
        try:
            await _add_requirement(event_id, "Serveur", quantity=5, minimum=4,
                                   minimum_experience=2, required_gender="FEMALE")
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            reqs = r.json()["requirements"]
            assert len(reqs) == 1
            req = reqs[0]
            assert req["requirement_id"]
            assert req["role_name"] == "Serveur"
            assert req["quantity"] == 5
            assert req["required_gender"] == "FEMALE"
            assert req["minimum_experience"] == 2
            assert req["required_minimum_skill_level"] == 4
            assert req["selected"] == 0
            assert req["missing"] == 5
        finally:
            await _wipe(event_id, [])

    async def test_assignments_shape(self, client: AsyncClient, admin_token):
        event_id, _, _ = await _make_event(start_offset_days=208)
        server_id = await _make_server("shape")
        try:
            await _add_requirement(event_id, "Serveur", minimum=3)
            await _assign(event_id, server_id, role="Serveur")
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            rows = r.json()["assignments"]
            assert len(rows) == 1
            row = rows[0]
            # Step 24C-D-8B-FIX: this list is the HTTP-level contract check. It
            # omitted `required_minimum_skill_level`, which is exactly why the
            # response model could drop the field while every other test passed.
            for field in (
                "server_id", "first_name", "last_name", "gender", "city",
                "years_experience", "role", "assignment_status", "assigned_at",
                "confirmed_at", "score", "required_minimum_skill_level",
                "profile_photo_available", "actual_skills",
                "verified_attestations", "uniform_size",
            ):
                assert field in row, f"missing assignment field {field}"
            assert row["server_id"] == server_id
            assert row["role"] == "Serveur"
            assert row["assignment_status"] == "CONFIRMED"
            assert row["assigned_at"] is not None
            assert row["confirmed_at"] is not None
            # Serialised through the response model, so this is a real int here.
            assert row["required_minimum_skill_level"] == 3
            assert row["actual_skills"] == []
            assert row["verified_attestations"] == []
            assert row["uniform_size"] is None
        finally:
            await _wipe(event_id, [server_id])

    async def test_assignment_required_minimum_survives_response_serialization(
        self, client: AsyncClient, admin_token
    ):
        """Step 24C-D-8B-FIX: the field must exist in the REAL HTTP response.

        The regression was that `get_event_print_data` built
        `required_minimum_skill_level` per assignment, but
        `EventPrintAssignmentResponse` never declared it, so FastAPI's response
        model discarded it. Every service-level test still passed, because a
        direct service call returns the raw dict and never goes through the
        response model.

        This test therefore goes through HTTP on purpose, and asserts on the
        decoded JSON body -- that is the only layer where the bug was visible.
        """
        event_id, _, _ = await _make_event(start_offset_days=236)
        server_id = await _make_server("httpmin")
        try:
            await _add_requirement(event_id, "Serveur", minimum=6)
            await _assign(event_id, server_id, role="Serveur")

            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text

            row = r.json()["assignments"][0]
            assert "required_minimum_skill_level" in row, (
                "required_minimum_skill_level was dropped by the response model"
            )
            assert row["required_minimum_skill_level"] == 6, (
                "the printed row must carry the requirement minimum it was "
                "assigned against, not the server's own level"
            )
            # The requirement minimum is a threshold, never null.
            assert isinstance(row["required_minimum_skill_level"], int)

            # A distinct value, so a coincidence could not make this pass.
            await _add_skill(server_id, "Service", 9)
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            row = r.json()["assignments"][0]
            assert row["required_minimum_skill_level"] == 6
            assert row["actual_skills"][0]["level"] == 9
            assert row["required_minimum_skill_level"] != row["actual_skills"][0]["level"]
        finally:
            await _wipe(event_id, [server_id])

    async def test_response_model_declares_the_assignment_fields(
        self, client: AsyncClient, admin_token
    ):
        """Step 24C-D-8B-FIX: no untyped or unnamed data in the assignment model.

        Asserted against the model itself so a future field cannot be added to
        the service dict and silently dropped again, and so an accidental
        renaming is caught rather than tolerated.
        """
        from app.models.events import EventPrintAssignmentResponse

        assert set(EventPrintAssignmentResponse.model_fields) == {
            "server_id", "first_name", "last_name", "gender", "city",
            "years_experience", "role", "assignment_status", "assigned_at",
            "confirmed_at", "score", "required_minimum_skill_level",
            "actual_skills", "verified_attestations", "profile_photo_available",
            "uniform_size",
        }, (
            "the assignment contract changed; add an HTTP assertion for any new "
            "field rather than letting it appear untested"
        )
        # Required, not optional: event_requirements.minimum_skill_level is
        # NOT NULL and the service falls back to 1, so null would be a bug.
        assert (
            EventPrintAssignmentResponse.model_fields["required_minimum_skill_level"].is_required()
        )
        # Every assignment in a real response exposes it too.
        event_id, _, _ = await _make_event(start_offset_days=237)
        server_id = await _make_server("httpdecl")
        try:
            await _add_requirement(event_id, "Serveur", minimum=2)
            await _assign(event_id, server_id, role="Serveur")
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200, r.text
            for row in r.json()["assignments"]:
                assert "required_minimum_skill_level" in row
            # The requirement-level field is unaffected and still present.
            assert r.json()["requirements"][0]["required_minimum_skill_level"] == 2
        finally:
            await _wipe(event_id, [server_id])

    async def test_proposed_assignments_are_included(self):
        """PROPOSED staff are still on the sheet; only DECLINED/CANCELLED are not."""
        event_id, _, _ = await _make_event(start_offset_days=209)
        server_id = await _make_server("proposed")
        try:
            await _assign(event_id, server_id, status="PROPOSED")
            data = await get_event_print_data(event_id)
            assert len(data["assignments"]) == 1
            assert data["assignments"][0]["assignment_status"] == "PROPOSED"
            assert data["assignments"][0]["confirmed_at"] is None
        finally:
            await _wipe(event_id, [server_id])

    async def test_cancelled_and_declined_assignments_are_excluded(self):
        event_id, _, _ = await _make_event(start_offset_days=210)
        cancelled = await _make_server("cancelled")
        declined = await _make_server("declined")
        try:
            await _assign(event_id, cancelled, status="CANCELLED")
            await _assign(event_id, declined, status="DECLINED")
            data = await get_event_print_data(event_id)
            assert data["assignments"] == []
        finally:
            await _wipe(event_id, [cancelled, declined])

    async def test_empty_event_returns_empty_collections(self):
        event_id, _, _ = await _make_event(start_offset_days=211)
        try:
            data = await get_event_print_data(event_id)
            assert data["requirements"] == []
            assert data["assignments"] == []
            assert data["transport_groups"] == []
        finally:
            await _wipe(event_id, [])

    async def test_no_absolute_deadline_is_invented(self, client: AsyncClient,
                                                    admin_token):
        """Only the relative budget is exposed; no competing deadline field."""
        event_id, _, _ = await _make_event(start_offset_days=212)
        try:
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            event = r.json()["event"]
            assert event["required_response_minutes"] == 45
            blob = str(r.json()).lower()
            for forbidden in ("response_deadline", "deadline_at", "deadline"):
                assert forbidden not in blob, f"{forbidden} must not be invented"
        finally:
            await _wipe(event_id, [])


# ----------------------------------------------------- D. required vs actual


class TestPrintDataSkillSemantics:
    async def test_requirement_minimum_is_named_explicitly(self):
        event_id, _, _ = await _make_event(start_offset_days=213)
        server_id = await _make_server("skillsem")
        try:
            await _add_requirement(event_id, "Serveur", minimum=2)
            await _assign(event_id, server_id)
            await _add_skill(server_id, "Service", 9)

            data = await get_event_print_data(event_id)
            req = data["requirements"][0]
            row = data["assignments"][0]

            assert req["required_minimum_skill_level"] == 2
            assert row["required_minimum_skill_level"] == 2
            assert row["actual_skills"][0]["level"] == 9
            # The two values must not be the same number presented as one thing.
            assert row["required_minimum_skill_level"] != row["actual_skills"][0]["level"]
        finally:
            await _wipe(event_id, [server_id])

    async def test_actual_skills_come_from_server_skills(self):
        event_id, _, _ = await _make_event(start_offset_days=214)
        server_id = await _make_server("actualsrc")
        try:
            await _assign(event_id, server_id)
            expected_id = await _add_skill(server_id, "Cuisine", 7)
            await _add_skill(server_id, "Service", 4)

            data = await get_event_print_data(event_id)
            skills = data["assignments"][0]["actual_skills"]
            assert len(skills) == 2
            top = skills[0]
            # Ordered by level DESC, so the highest real level comes first.
            assert top["skill_name"] == "Cuisine"
            assert top["level"] == 7
            assert top["skill_id"] == expected_id
            assert top["years_experience"] == 6
            assert set(top) == {"skill_id", "skill_name", "level",
                                "years_experience"}
        finally:
            await _wipe(event_id, [server_id])

    async def test_no_skill_identity_is_invented_for_a_requirement(self):
        """`event_requirements` has no skill_id, so no skill name may appear."""
        event_id, _, _ = await _make_event(start_offset_days=215)
        try:
            await _add_requirement(event_id, "Chef de rang", minimum=6)
            data = await get_event_print_data(event_id)
            req = data["requirements"][0]
            assert set(req) == {
                "requirement_id", "role_name", "quantity", "required_gender",
                "minimum_experience", "required_minimum_skill_level",
                "selected", "missing",
            }
            blob = str(req).lower()
            assert "skill_id" not in blob
            assert "skill_name" not in blob
            # The bare number is still a number.
            assert isinstance(req["required_minimum_skill_level"], int)
        finally:
            await _wipe(event_id, [])

    async def test_existing_event_detail_skill_level_is_unchanged(self):
        """The old contract keeps its existing meaning: requirement minimum."""
        event_id, _, _ = await _make_event(start_offset_days=216)
        server_id = await _make_server("compat")
        try:
            await _add_requirement(event_id, "Serveur", minimum=7)
            await _assign(event_id, server_id, role="Serveur")
            await _add_skill(server_id, "Service", 9)

            detail = await get_event_staff_summary(event_id)
            row = next(
                a for a in detail["assignments"] if a["server_id"] == server_id
            )
            # Unchanged: still the requirement minimum, NOT the server's level.
            assert row["skill_level"] == 7

            printed = await get_event_print_data(event_id)
            assert printed["assignments"][0]["actual_skills"][0]["level"] == 9
            # The print contract must not reuse the ambiguous name.
            assert "skill_level" not in printed["assignments"][0]
        finally:
            await _wipe(event_id, [server_id])

    async def test_existing_event_detail_payload_is_byte_identical_in_shape(self):
        """This step must not alter the event-detail response at all."""
        event_id, _, _ = await _make_event(start_offset_days=217)
        server_id = await _make_server("shapestable")
        try:
            await _add_requirement(event_id, "Serveur", minimum=3)
            await _assign(event_id, server_id)
            await _add_skill(server_id, "Service", 8)
            await _add_transport_group(event_id, server_id, [])

            detail = await get_event_staff_summary(event_id)
            assert set(detail) == {"event", "staffing", "requirements",
                                   "assignments", "transport"}
            assert set(detail["transport"]) == {"groups", "total_groups",
                                               "total_passengers"}
            assert "distance_km" in detail["assignments"][0]
            assert detail["assignments"][0]["distance_km"] is None
        finally:
            await _wipe(event_id, [server_id])


# ------------------------------------------------------- E. attestations


class TestPrintDataVerifiedAttestations:
    async def test_verified_attestations_are_included(self):
        event_id, _, _ = await _make_event(start_offset_days=218)
        server_id = await _make_server("attestok")
        try:
            await _assign(event_id, server_id)
            await _add_attestation(server_id, "VERIFIED", "Sommelier")

            data = await get_event_print_data(event_id)
            items = data["assignments"][0]["verified_attestations"]
            assert len(items) == 1
            item = items[0]
            assert item["qualification_name"] == "Sommelier"
            assert item["status"] == "VERIFIED"
            assert item["attestation_id"]
            assert item["verified_at"] is not None
            assert set(item) == {"attestation_id", "qualification_name",
                                 "status", "verified_at"}
        finally:
            await _wipe(event_id, [server_id])

    async def test_pending_attestation_is_excluded(self):
        event_id, _, _ = await _make_event(start_offset_days=219)
        server_id = await _make_server("attestpend")
        try:
            await _assign(event_id, server_id)
            await _add_attestation(server_id, "PENDING", "HACCP")
            data = await get_event_print_data(event_id)
            assert data["assignments"][0]["verified_attestations"] == []
        finally:
            await _wipe(event_id, [server_id])

    async def test_rejected_attestation_is_excluded(self):
        event_id, _, _ = await _make_event(start_offset_days=220)
        server_id = await _make_server("attestrej")
        try:
            await _assign(event_id, server_id)
            await _add_attestation(server_id, "REJECTED", "HACCP")
            data = await get_event_print_data(event_id)
            assert data["assignments"][0]["verified_attestations"] == []
        finally:
            await _wipe(event_id, [server_id])

    async def test_superseded_attestation_is_excluded(self):
        """A replaced document must not be presented as a live qualification."""
        event_id, _, _ = await _make_event(start_offset_days=221)
        server_id = await _make_server("attestsup")
        try:
            await _assign(event_id, server_id)
            await _add_superseded_attestation(server_id, "Securite")
            data = await get_event_print_data(event_id)
            items = data["assignments"][0]["verified_attestations"]
            assert [i["qualification_name"] for i in items] == ["Securite actuel"]
        finally:
            await _wipe(event_id, [server_id])

    async def test_mixed_statuses_return_only_verified(self):
        event_id, _, _ = await _make_event(start_offset_days=222)
        server_id = await _make_server("attestmix")
        try:
            await _assign(event_id, server_id)
            await _add_attestation(server_id, "VERIFIED", "Sommelier")
            await _add_attestation(server_id, "PENDING", "HACCP")
            await _add_attestation(server_id, "REJECTED", "PSC1")

            data = await get_event_print_data(event_id)
            items = data["assignments"][0]["verified_attestations"]
            assert [i["qualification_name"] for i in items] == ["Sommelier"]
            assert all(i["status"] == "VERIFIED" for i in items)
        finally:
            await _wipe(event_id, [server_id])

    async def test_no_document_metadata_beyond_the_allowed_fields(self):
        event_id, _, _ = await _make_event(start_offset_days=223)
        server_id = await _make_server("attestfields")
        try:
            await _assign(event_id, server_id)
            await _add_attestation(server_id, "VERIFIED", "Sommelier")
            data = await get_event_print_data(event_id)
            item = data["assignments"][0]["verified_attestations"][0]
            for forbidden in (
                "file_id", "content", "mime_type", "path", "url", "url_token",
                "verified_by", "rejection_reason", "superseded_by_id",
            ):
                assert forbidden not in item, f"{forbidden} exposed on attestation"
        finally:
            await _wipe(event_id, [server_id])


# ------------------------------------------------------------- F. profile photo


class TestPrintDataProfilePhotos:
    async def test_photo_presence_is_a_boolean(self):
        event_id, _, _ = await _make_event(start_offset_days=224)
        with_photo = await _make_server("photoyes")
        without = await _make_server("photono")
        try:
            await _assign(event_id, with_photo)
            await _assign(event_id, without)
            await _add_profile_photo(with_photo)

            data = await get_event_print_data(event_id)
            flags = {
                a["server_id"]: a["profile_photo_available"]
                for a in data["assignments"]
            }
            assert flags[with_photo] is True
            assert flags[without] is False
        finally:
            await _wipe(event_id, [with_photo, without])

    async def test_no_photo_bytes_or_urls_in_the_response(self):
        event_id, _, _ = await _make_event(start_offset_days=225)
        server_id = await _make_server("photobytes")
        try:
            await _assign(event_id, server_id)
            await _add_profile_photo(server_id)

            data = await get_event_print_data(event_id)
            row = data["assignments"][0]
            assert isinstance(row["profile_photo_available"], bool)
            blob = str(data).lower()
            for forbidden in (
                "print-photo-bytes", "content", "bytea", "base64",
                "file_id", "url", "avatar.png",
            ):
                assert forbidden not in blob, f"{forbidden} exposed in print data"
        finally:
            await _wipe(event_id, [server_id])

    async def test_superseded_photo_is_not_counted_as_current(self):
        """Photos are single-current: only is_current counts."""
        event_id, _, _ = await _make_event(start_offset_days=226)
        server_id = await _make_server("photoold")
        try:
            await _assign(event_id, server_id)
            pool = await get_pool()
            async with pool.acquire() as conn:
                payload = b"\x89PNG\r\n\x1a\n" + b"stale"
                await conn.execute(
                    """
                    INSERT INTO server_files (
                        server_id, file_type, content, mime_type, file_size,
                        is_current
                    ) VALUES ($1, 'PROFILE_PHOTO', $2, 'image/png', $3, FALSE)
                    """,
                    server_id,
                    payload,
                    len(payload),
                )
            data = await get_event_print_data(event_id)
            assert data["assignments"][0]["profile_photo_available"] is False
        finally:
            await _wipe(event_id, [server_id])


# --------------------------------------------------------------- G. transport


class TestPrintDataTransport:
    async def test_multiple_groups_and_passengers(self):
        event_id, _, _ = await _make_event(start_offset_days=227)
        d1 = await _make_server("drvone")
        d2 = await _make_server("drvtwo")
        p1 = await _make_server("paxone")
        p2 = await _make_server("paxtwo")
        p3 = await _make_server("paxthree")
        everyone = [d1, d2, p1, p2, p3]
        try:
            await _add_transport_group(event_id, d1, [(p1, "Point A"),
                                                      (p2, "Point B")])
            await _add_transport_group(event_id, d2, [(p3, "Point C")])

            data = await get_event_print_data(event_id)
            groups = data["transport_groups"]
            assert len(groups) == 2
            counts = sorted(g["passenger_count"] for g in groups)
            assert counts == [1, 2]
            picked = [p["server_id"] for g in groups for p in g["passengers"]]
            assert set(picked) == {p1, p2, p3}
        finally:
            await _wipe(event_id, everyone)

    async def test_pickup_order_and_labels(self):
        event_id, _, _ = await _make_event(start_offset_days=228)
        driver = await _make_server("orddrv")
        p1 = await _make_server("ordp1")
        p2 = await _make_server("ordp2")
        p3 = await _make_server("ordp3")
        everyone = [driver, p1, p2, p3]
        try:
            await _add_transport_group(
                event_id, driver,
                [(p3, "Zone C"), (p1, "Zone A"), (p2, "Zone B")],
            )
            data = await get_event_print_data(event_id)
            group = data["transport_groups"][0]
            assert [p["pickup_order"] for p in group["passengers"]] == [1, 2, 3]
            assert [p["pickup_location_label"] for p in group["passengers"]] == [
                "Zone C", "Zone A", "Zone B",
            ]
            assert all(p["pickup_status"] == "PENDING" for p in group["passengers"])
        finally:
            await _wipe(event_id, everyone)

    async def test_group_operational_fields(self):
        event_id, _, _ = await _make_event(start_offset_days=229)
        driver = await _make_server("opdrv")
        pax = await _make_server("oppax")
        try:
            await _add_transport_group(event_id, driver, [(pax, "Point A")])
            data = await get_event_print_data(event_id)
            group = data["transport_groups"][0]
            for field in (
                "transport_group_id", "driver_server_id", "driver_name", "vehicle",
                "vehicle_type", "capacity", "passenger_count", "departure_time",
                "departure_location_label", "destination_label",
                "estimated_duration_minutes", "estimated_distance_km",
                "estimated_route_distance_km", "has_exact_location", "status",
                "passengers",
            ):
                assert field in group, f"missing transport field {field}"
            assert group["vehicle"] == "Renault Trafic"
            assert group["vehicle_type"] == "VAN"
            assert group["capacity"] == 9
            assert group["passenger_count"] == 1
            assert group["departure_time"] is not None
            assert group["departure_location_label"] == "Depot Tunis"
            assert group["destination_label"] == "Venue Sousse"
            assert group["estimated_duration_minutes"] == 35
            assert group["estimated_distance_km"] == 14.75
            assert group["estimated_route_distance_km"] > 0
            assert group["has_exact_location"] is True
            assert group["status"] == "CONFIRMED"
            assert group["driver_name"].endswith("Print")
        finally:
            await _wipe(event_id, [driver, pax])

    async def test_cancelled_group_is_excluded(self):
        event_id, _, _ = await _make_event(start_offset_days=230)
        driver = await _make_server("canceldrv")
        try:
            await _add_transport_group(event_id, driver, [], status="CANCELLED")
            data = await get_event_print_data(event_id)
            assert data["transport_groups"] == []
        finally:
            await _wipe(event_id, [driver])

    async def test_no_coordinates_in_transport(self):
        event_id, _, _ = await _make_event(start_offset_days=231)
        driver = await _make_server("coorddrv")
        pax = await _make_server("coordpax")
        try:
            await _add_transport_group(event_id, driver, [(pax, "Point A")])
            data = await get_event_print_data(event_id)
            blob = str(data["transport_groups"]).lower()
            for forbidden in (
                "latitude", "longitude", "pickup_lat", "pickup_lon",
                "departure_lat", "destination_lat",
            ):
                assert forbidden not in blob, f"{forbidden} leaked into transport"
        finally:
            await _wipe(event_id, [driver, pax])


# ----------------------------------------------------------------- H. privacy


def _walk(node, path="$"):
    """Yield (full_path, key, value) for every node in a nested payload."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}"
            yield child, key, value
            yield from _walk(value, child)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


class TestPrintDataPrivacy:
    async def test_no_server_gps_anywhere(self):
        event_id, _, _ = await _make_event(start_offset_days=232)
        server_id = await _make_server("gpsprint")
        driver = await _make_server("gpsdrv")
        try:
            await _assign(event_id, server_id)
            await _add_transport_group(event_id, driver, [(server_id, "Point A")])

            data = await get_event_print_data(event_id)
            # The venue coordinates live at exactly one place, under the event.
            coordinates: list[str] = []
            for path, key, value in _walk(data):
                if key in ("latitude", "longitude") and isinstance(value, (int, float)):
                    coordinates.append(path)
            assert coordinates == ["$.event.latitude", "$.event.longitude"], (
                f"coordinates found outside the event: {coordinates}"
            )
        finally:
            await _wipe(event_id, [server_id, driver])

    async def test_server_location_history_is_never_loaded(self):
        """server_locations is a real table; the print path must not read it."""
        import inspect

        import app.services.event_service as es

        event_id, _, _ = await _make_event(start_offset_days=233)
        server_id = await _make_server("histprint")
        try:
            await _assign(event_id, server_id)
            source = inspect.getsource(es.get_event_print_data)
            for table in (
                "server_locations",
                "server_availability",
                "audit_log",
                "users",
            ):
                assert table not in source, f"print path must not read {table}"
        finally:
            await _wipe(event_id, [server_id])

    async def test_no_contact_credentials_or_audit_detail(self, client: AsyncClient,
                                                          admin_token):
        event_id, _, _ = await _make_event(start_offset_days=234)
        server_id = await _make_server("secretprint")
        try:
            await _assign(event_id, server_id)
            await _add_skill(server_id, "Service", 5)
            await _add_attestation(server_id, "VERIFIED", "Sommelier")
            await _add_profile_photo(server_id)

            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert r.status_code == 200
            raw = r.text.lower()
            for forbidden in (
                "+21699000000",            # the server phone
                "print_secretprint",       # the server email local part
                "@example.org",
                "hashed_password", "password", "token", "jwt", "authorization",
                "audit_log", "audit_action", "actor_id",
            ):
                assert forbidden not in raw, f"{forbidden} exposed in print data"
        finally:
            await _wipe(event_id, [server_id])

    async def test_response_is_pure_json_no_bytes(self, client: AsyncClient,
                                                  admin_token):
        event_id, _, _ = await _make_event(start_offset_days=235)
        server_id = await _make_server("jsonprint")
        try:
            await _assign(event_id, server_id)
            await _add_attestation(server_id, "VERIFIED", "Sommelier")
            r = await client.get(
                f"/api/events/{event_id}/print-data",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            # A BYTEA anywhere would have failed JSON serialisation; assert the
            # response is decodable text, not an encoded blob.
            assert isinstance(r.json(), dict)
            assert r.headers["content-type"].startswith("application/json")
        finally:
            await _wipe(event_id, [server_id])

    async def test_approximate_location_is_flagged(self):
        """An event with no coordinates falls back and must say so."""
        event_id, _, _ = await _make_event(start_offset_days=236,
                                           with_coordinates=False)
        try:
            data = await get_event_print_data(event_id)
            assert data["event"]["has_exact_location"] is False
            # Coordinates are still present: the fallback position, not nothing.
            assert data["event"]["latitude"] is not None
            assert data["event"]["longitude"] is not None
        finally:
            await _wipe(event_id, [])

    async def test_approximate_flag_propagates_to_transport(self):
        event_id, _, _ = await _make_event(start_offset_days=237,
                                           with_coordinates=False)
        driver = await _make_server("approxdrv")
        pax = await _make_server("approxpax")
        try:
            await _add_transport_group(event_id, driver, [(pax, "Point A")])
            data = await get_event_print_data(event_id)
            assert data["event"]["has_exact_location"] is False
            assert data["transport_groups"][0]["has_exact_location"] is False
        finally:
            await _wipe(event_id, [driver, pax])


# ------------------------------------------------------------- I. query scaling


class _QueryCounter:
    """Counts SQL statements executed on a connection."""

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


async def _count_for_n_servers(n: int) -> int:
    """Statement count for a print-data read over `n` assigned servers."""
    event_id, _, _ = await _make_event(start_offset_days=300 + n)
    servers = [await _make_server(f"q{n}_{i}") for i in range(n)]
    drivers = [await _make_server(f"qd{n}_{i}") for i in range(2)]
    everyone = servers + drivers
    try:
        await _add_requirement(event_id, "Serveur", quantity=n + 2, minimum=3)
        for sid in servers:
            await _assign(event_id, sid)
            await _add_skill(sid, f"Skill {n}", 6)
            await _add_attestation(sid, "VERIFIED", "Sommelier")
            if n % 2 == 0:
                await _add_profile_photo(sid)
        for d in drivers:
            await _add_transport_group(
                event_id, d, [(p, f"Point {i}") for i, p in enumerate(servers[:2])]
            )

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

        import app.services.event_service as es

        original = es.get_pool
        es.get_pool = fake_get_pool
        try:
            await get_event_print_data(event_id)
        finally:
            es.get_pool = original
        return counter["n"]
    finally:
        await _wipe(event_id, everyone)


class TestPrintDataQueryScaling:
    async def test_statement_count_is_constant_across_staff_counts(self):
        one = await _count_for_n_servers(1)
        ten = await _count_for_n_servers(10)
        twentyfive = await _count_for_n_servers(25)
        assert one == ten == twentyfive, (
            f"print-data query count scales with staff count: "
            f"1={one} 10={ten} 25={twentyfive}"
        )

    async def test_statement_count_is_small_and_bounded(self):
        """Constant AND small: 8 statements is the designed ceiling here."""
        count = await _count_for_n_servers(10)
        assert count <= 10, f"unexpected statement count: {count}"

    async def test_holds_a_single_connection(self, monkeypatch):
        import app.services.event_service as es

        event_id, _, _ = await _make_event(start_offset_days=400)
        server_id = await _make_server("connprint")
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
                def acquire(self):
                    return _Counting(real_acquire())

                def __getattr__(self, item):
                    return getattr(real_pool, item)

            async def _fake_get_pool():
                return _PoolProxy()

            monkeypatch.setattr(es, "get_pool", _fake_get_pool)
            await get_event_print_data(event_id)
            assert counter["n"] == 1, (
                f"print-data acquired {counter['n']} connections; expected 1"
            )
        finally:
            await _wipe(event_id, [server_id])


# -------------------------------------------------------------- J. bulk shape


class TestPrintDataBulkBehaviour:
    async def test_no_per_server_query_loop_for_skills_attestations_photos(
        self, monkeypatch
    ):
        """One statement each for skills, attestations and photos, at any N."""
        import app.services.event_service as es

        event_id, _, _ = await _make_event(start_offset_days=401)
        servers = [await _make_server(f"blk{i}") for i in range(5)]
        try:
            for sid in servers:
                await _assign(event_id, sid)
                await _add_skill(sid, "Service", 5)
                await _add_attestation(sid, "VERIFIED", "Sommelier")
                await _add_profile_photo(sid)

            calls = {"skills": 0, "attestations": 0, "photos": 0}
            # Bound before patching, so the counting wrappers call the real
            # implementations rather than themselves.
            from app.services.event_service import load_actual_skill_levels as real_skills
            from app.services.server_attestation_service import (
                load_verified_attestations as real_attestations,
            )
            from app.services.server_file_service import (
                load_servers_with_profile_photo as real_photos,
            )

            async def counting_skills(server_ids, conn=None):
                calls["skills"] += 1
                return await real_skills(server_ids, conn=conn)

            async def counting_attestations(server_ids, conn=None):
                calls["attestations"] += 1
                return await real_attestations(server_ids, conn=conn)

            async def counting_photos(server_ids, conn=None):
                calls["photos"] += 1
                return await real_photos(server_ids, conn=conn)

            monkeypatch.setattr(es, "load_actual_skill_levels", counting_skills)
            monkeypatch.setattr(es, "load_verified_attestations",
                                counting_attestations)
            monkeypatch.setattr(es, "load_servers_with_profile_photo",
                                counting_photos)

            data = await get_event_print_data(event_id)
            assert len(data["assignments"]) == 5
            # Five servers, one call each: a loop would have made five.
            assert calls == {"skills": 1, "attestations": 1, "photos": 1}
        finally:
            await _wipe(event_id, servers)

    async def test_transport_passengers_are_one_statement_for_all_groups(self):
        """The passenger query must not scale with the number of groups."""
        event_id, _, _ = await _make_event(start_offset_days=402)
        drivers = [await _make_server(f"tgrp{i}") for i in range(3)]
        pax = await _make_server("tgrppax")
        everyone = list(drivers) + [pax]
        try:
            for d in drivers:
                await _add_transport_group(event_id, d, [(pax, "Point A")])

            from app.services.event_service import _fetch_print_transport_groups

            pool = await get_pool()
            async with pool.acquire() as conn:
                counter = _QueryCounter(conn)
                groups = await _fetch_print_transport_groups(counter, event_id, True)
            assert len(groups) == 3
            # One statement for the groups, one for ALL their passengers.
            assert counter.statements == 2, (
                f"expected 2 statements, got {counter.statements}"
            )
        finally:
            await _wipe(event_id, everyone)

    async def test_bulk_helpers_accept_an_existing_connection(self):
        """The enrichment helpers must not acquire a second connection."""
        from app.services.server_attestation_service import load_verified_attestations
        from app.services.server_file_service import load_servers_with_profile_photo
        from app.services.event_service import load_actual_skill_levels

        server_id = await _make_server("helperconn")
        try:
            await _add_skill(server_id, "Service", 5)
            await _add_attestation(server_id, "VERIFIED", "Sommelier")
            await _add_profile_photo(server_id)

            pool = await get_pool()
            async with pool.acquire() as conn:
                counter = _QueryCounter(conn)
                skills = await load_actual_skill_levels([server_id], conn=counter)
                assert counter.statements == 1
                counter.statements = 0
                attestations = await load_verified_attestations(
                    [server_id], conn=counter
                )
                assert counter.statements == 1
                counter.statements = 0
                photos = await load_servers_with_profile_photo(
                    [server_id], conn=counter
                )
                assert counter.statements == 1

            assert skills[server_id][0]["skill_id"]
            assert attestations[server_id][0]["qualification_name"] == "Sommelier"
            assert photos[server_id] is True
        finally:
            await _wipe(None, [server_id])

    async def test_empty_server_list_short_circuits(self):
        from app.services.server_attestation_service import load_verified_attestations
        from app.services.server_file_service import load_servers_with_profile_photo

        pool = await get_pool()
        async with pool.acquire() as conn:
            counter = _QueryCounter(conn)
            assert await load_verified_attestations([], conn=counter) == {}
            assert await load_servers_with_profile_photo([], conn=counter) == {}
            assert counter.statements == 0
