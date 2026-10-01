"""Step 24C-D-7: audit logging for profile photos and attestations.

Two invariants drive every test here.

1. ATOMICITY. An audit row is written in the SAME transaction as the change it
   describes. A rolled-back mutation must therefore leave no audit row, and a
   committed mutation must always leave one. A record claiming a photo was
   deleted, or an attestation verified, when it was not, is the specific failure
   mode being guarded against.

2. METADATA ONLY. Audit detail is an explicit whitelist. Document bytes, GPS,
   credentials and URLs must never appear in the JSONB detail.

Server actions deliberately keep `target_user_id` NULL: audit_log's
target_user_id is a foreign key onto users(id), so a server id cannot be stored
there. The server is identified by detail->>'server_id'.
"""

import json
import uuid

import pytest
from httpx import AsyncClient

from app.core.database import get_pool
from app.services.auth_service import get_user_by_email

ADMIN_EMAIL = "admin@le-seizieme.local"

# Every audit action this step introduces.
AUDIT_PROFILE_PHOTO_UPLOADED = "PROFILE_PHOTO_UPLOADED"
AUDIT_PROFILE_PHOTO_DELETED = "PROFILE_PHOTO_DELETED"
AUDIT_ATTESTATION_UPLOADED = "ATTESTATION_UPLOADED"
AUDIT_ATTESTATION_VERIFIED = "ATTESTATION_VERIFIED"
AUDIT_ATTESTATION_REJECTED = "ATTESTATION_REJECTED"
AUDIT_ATTESTATION_SUPERSEDED = "ATTESTATION_SUPERSEDED"

SERVER_AUDIT_ACTIONS = (
    AUDIT_PROFILE_PHOTO_UPLOADED,
    AUDIT_PROFILE_PHOTO_DELETED,
    AUDIT_ATTESTATION_UPLOADED,
    AUDIT_ATTESTATION_VERIFIED,
    AUDIT_ATTESTATION_REJECTED,
    AUDIT_ATTESTATION_SUPERSEDED,
)

# Substrings that must never reach an audit detail for these events.
FORBIDDEN_IN_DETAIL = (
    "password",
    "hashed",
    "secret",
    "token",
    "jwt",
    "bearer",
    "credential",
    "api_key",
    "apikey",
    "latitude",
    "longitude",
    "gps",
    "http://",
    "https://",
    "s3://",
    "presign",
    "content",
    "bytes",
)


# ----------------------------------------------------------------- utilities


def _png_bytes() -> bytes:
    """Smallest byte-accurate PNG (1x1 truecolour)."""
    import zlib

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            len(payload).to_bytes(4, "big")
            + kind
            + payload
            + zlib.crc32(kind + payload).to_bytes(4, "big")
        )

    ihdr = (
        (1).to_bytes(4, "big")
        + (1).to_bytes(4, "big")
        + bytes([8, 2, 0, 0, 0])
        + b"\x00\x00\x00"
    )
    raw = b"\x00" + b"\xff\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )


def _fake_pdf() -> bytes:
    """PDF marker without a version: must be rejected by magic-byte sniffing."""
    return b"%PDF-notreally\n" + b"\x00" * 32


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _upload(data: bytes, filename: str, content_type: str):
    return {"file": (filename, data, content_type)}


def _att_upload(data: bytes, filename: str, content_type: str, **fields):
    """Document in `files`, metadata in `data` (httpx encodes all files as parts)."""
    import io

    return {
        "files": {"file": (filename, io.BytesIO(data), content_type)},
        "data": {k: v for k, v in fields.items() if v is not None},
    }


async def _new_server(tag: str) -> str:
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
            VALUES ($1, $2, 'Audited', '+21600000000', $3, 'MALE', $4, 3)
            """,
            server_id,
            tag[:1].upper() + tag[1:],
            f"aud_{tag}_{server_id}@example.org",
            city_id,
        )
    return str(server_id)


async def _drop_servers(server_ids: list[str]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        for sid in server_ids:
            await conn.execute(
                "UPDATE server_attestations SET superseded_by_id = NULL "
                "WHERE server_id = $1",
                sid,
            )
            await conn.execute("DELETE FROM server_attestations WHERE server_id = $1", sid)
            await conn.execute("DELETE FROM server_files WHERE server_id = $1", sid)
            await conn.execute("DELETE FROM servers WHERE id = $1", sid)


async def _count_action(pool, action: str) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT count(*) FROM audit_log WHERE action = $1", action
        )


async def _latest_action(pool, action: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT actor_user_id, target_user_id, detail
            FROM audit_log
            WHERE action = $1
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            action,
        )
    if row is None:
        return None
    detail = row["detail"]
    if isinstance(detail, str):
        detail = json.loads(detail)
    return {
        "actor_user_id": str(row["actor_user_id"]) if row["actor_user_id"] else None,
        "target_user_id": str(row["target_user_id"]) if row["target_user_id"] else None,
        "detail": detail or {},
    }


async def _admin_id() -> str:
    admin = await get_user_by_email(ADMIN_EMAIL)
    assert admin is not None
    return str(admin["id"])


def _assert_no_sensitive(detail: dict) -> None:
    """Fail if any forbidden key or value pattern reached the audit detail."""
    blob = json.dumps(detail).lower()
    for needle in FORBIDDEN_IN_DETAIL:
        assert needle not in blob, (
            f"audit detail leaked {needle!r}: {json.dumps(detail)[:400]}"
        )


# ------------------------------------------------------------- enum coverage


class TestAuditEnumExpansion:
    async def test_six_new_actions_exist(self, pool):
        async with pool.acquire() as conn:
            labels = [
                r["enumlabel"]
                for r in await conn.fetch(
                    """
                    SELECT enumlabel FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'admin_audit_action'
                    """
                )
            ]
        for action in SERVER_AUDIT_ACTIONS:
            assert action in labels, f"{action} missing from admin_audit_action"

    async def test_photo_upload_and_replace_share_one_action(self, pool):
        """There is deliberately no separate REPLACED action."""
        async with pool.acquire() as conn:
            labels = [
                r["enumlabel"]
                for r in await conn.fetch(
                    """
                    SELECT enumlabel FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'admin_audit_action'
                    """
                )
            ]
        assert "SERVER_FILE_REPLACED" not in labels
        assert "PROFILE_PHOTO_REPLACED" not in labels

    async def test_original_user_actions_preserved(self, pool):
        async with pool.acquire() as conn:
            labels = [
                r["enumlabel"]
                for r in await conn.fetch(
                    """
                    SELECT enumlabel FROM pg_enum e
                    JOIN pg_type t ON t.oid = e.enumtypid
                    WHERE t.typname = 'admin_audit_action'
                    """
                )
            ]
        for legacy in ("USER_CREATED", "USER_UPDATED", "USER_DEACTIVATED"):
            assert legacy in labels


# -------------------------------------------------------------- 1. photo log


class TestProfilePhotoAudit:
    async def test_upload_creates_audit_action(self, client: AsyncClient, pool, admin_token):
        sid = await _new_server("pupload")
        try:
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 201, r.text
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            assert row is not None
            assert row["detail"]["server_id"] == sid
            assert row["detail"]["mime_type"] == "image/png"
            assert row["detail"]["file_size"] > 0
            assert row["detail"]["file_id"]
        finally:
            await _drop_servers([sid])

    async def test_initial_upload_has_replaced_false(self, client: AsyncClient, pool, admin_token):
        sid = await _new_server("pfirst")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            assert row["detail"]["replaced"] is False
        finally:
            await _drop_servers([sid])

    async def test_replacement_has_replaced_true(self, client: AsyncClient, pool, admin_token):
        sid = await _new_server("preplace")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "a.png", "image/png"),
                headers=_auth(admin_token),
            )
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "b.png", "image/png"),
                headers=_auth(admin_token),
            )
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            assert row["detail"]["replaced"] is True
        finally:
            await _drop_servers([sid])

    async def test_delete_creates_audit_action(self, client: AsyncClient, pool, admin_token):
        sid = await _new_server("pdelete")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            r = await client.delete(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_DELETED)
            assert row is not None
            assert row["detail"]["server_id"] == sid
            assert row["detail"]["file_id"]
            assert row["detail"]["mime_type"] == "image/png"
            assert row["detail"]["file_size"] > 0
        finally:
            await _drop_servers([sid])

    async def test_delete_of_absent_photo_creates_no_audit(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("pnoaudit")
        try:
            before = await _count_action(pool, AUDIT_PROFILE_PHOTO_DELETED)
            r = await client.delete(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert r.status_code == 404
            assert await _count_action(pool, AUDIT_PROFILE_PHOTO_DELETED) == before
        finally:
            await _drop_servers([sid])

    async def test_failed_upload_creates_no_audit(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("pfailed")
        try:
            before = await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(b"not-an-image", "x.png", "image/png"),
                headers=_auth(admin_token),
            )
            assert r.status_code >= 400
            assert await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED) == before
        finally:
            await _drop_servers([sid])

    async def test_upload_to_unknown_server_creates_no_audit(
        self, client: AsyncClient, pool, admin_token
    ):
        before = await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
        r = await client.put(
            f"/api/servers/{uuid.uuid4()}/files/profile-photo",
            files=_upload(_png_bytes(), "p.png", "image/png"),
            headers=_auth(admin_token),
        )
        assert r.status_code == 404
        assert await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED) == before

    async def test_photo_audit_detail_is_metadata_only(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("pmeta")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            _assert_no_sensitive(row["detail"])
            assert set(row["detail"]) == {
                "server_id",
                "file_id",
                "mime_type",
                "file_size",
                "replaced",
            }
        finally:
            await _drop_servers([sid])


# ------------------------------------------------------ 2. attestation audit


class TestAttestationAudit:
    async def _upload(self, client, token, sid, name="Sommelier"):
        r = await client.post(
            f"/api/servers/{sid}/attestations",
            **_att_upload(
                _pdf_bytes(),
                "c.pdf",
                "application/pdf",
                qualification_name=name,
            ),
            headers=_auth(token),
        )
        assert r.status_code == 201, r.text
        return r.json()

    async def test_upload_creates_audit_action(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("aupload")
        try:
            att = await self._upload(client, admin_token, sid)
            row = await _latest_action(pool, AUDIT_ATTESTATION_UPLOADED)
            assert row is not None
            d = row["detail"]
            assert d["server_id"] == sid
            assert d["attestation_id"] == att["id"]
            assert d["qualification_name"] == "Sommelier"
            assert d["mime_type"] == "application/pdf"
            assert d["file_size"] > 0
            assert d["status"] == "PENDING"
        finally:
            await _drop_servers([sid])

    async def test_verify_creates_audit_action(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("averify")
        try:
            att = await self._upload(client, admin_token, sid)
            r = await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/verify",
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            row = await _latest_action(pool, AUDIT_ATTESTATION_VERIFIED)
            assert row is not None
            d = row["detail"]
            assert d["server_id"] == sid
            assert d["attestation_id"] == att["id"]
            assert d["old_status"] == "PENDING"
            assert d["new_status"] == "VERIFIED"
            assert d["qualification_name"] == "Sommelier"
            assert d["verified_by"] is not None
            assert d["verified_at"] is not None
            _assert_no_sensitive(d)
        finally:
            await _drop_servers([sid])

    async def test_reject_creates_audit_action_with_reason(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("areject")
        try:
            att = await self._upload(client, admin_token, sid)
            r = await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/reject",
                json={"rejection_reason": "Certificat expiré"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            row = await _latest_action(pool, AUDIT_ATTESTATION_REJECTED)
            assert row is not None
            d = row["detail"]
            assert d["old_status"] == "PENDING"
            assert d["new_status"] == "REJECTED"
            assert d["rejection_reason"] == "Certificat expiré"
            _assert_no_sensitive(d)
        finally:
            await _drop_servers([sid])

    async def test_supersede_creates_audit_action(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("asuper")
        try:
            first = await self._upload(client, admin_token, sid)
            second = await self._upload(client, admin_token, sid)
            await client.patch(
                f"/api/servers/{sid}/attestations/{first['id']}/verify",
                headers=_auth(admin_token),
            )
            r = await client.patch(
                f"/api/servers/{sid}/attestations/{first['id']}/supersede",
                json={"superseded_by_id": second["id"]},
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            row = await _latest_action(pool, AUDIT_ATTESTATION_SUPERSEDED)
            assert row is not None
            d = row["detail"]
            assert d["attestation_id"] == first["id"]
            assert d["old_status"] == "VERIFIED"
            assert d["new_status"] == "SUPERSEDED"
            assert d["superseded_by_id"] == second["id"]
            _assert_no_sensitive(d)
        finally:
            await _drop_servers([sid])

    async def test_invalid_transition_creates_no_audit(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("abadminvalid")
        try:
            att = await self._upload(client, admin_token, sid)
            await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/verify",
                headers=_auth(admin_token),
            )
            before_v = await _count_action(pool, AUDIT_ATTESTATION_VERIFIED)
            before_r = await _count_action(pool, AUDIT_ATTESTATION_REJECTED)
            # VERIFIED -> REJECTED is not a legal transition.
            r = await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/reject",
                json={"rejection_reason": "tentative"},
                headers=_auth(admin_token),
            )
            assert r.status_code == 409
            assert await _count_action(pool, AUDIT_ATTESTATION_VERIFIED) == before_v
            assert await _count_action(pool, AUDIT_ATTESTATION_REJECTED) == before_r
        finally:
            await _drop_servers([sid])

    async def test_supersede_without_replacement_creates_no_audit(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("anorepl")
        try:
            att = await self._upload(client, admin_token, sid)
            await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/verify",
                headers=_auth(admin_token),
            )
            before = await _count_action(pool, AUDIT_ATTESTATION_SUPERSEDED)
            r = await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/supersede",
                json={},
                headers=_auth(admin_token),
            )
            assert r.status_code == 400
            assert await _count_action(pool, AUDIT_ATTESTATION_SUPERSEDED) == before
        finally:
            await _drop_servers([sid])

    async def test_failed_upload_creates_no_audit(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("aufail")
        try:
            before = await _count_action(pool, AUDIT_ATTESTATION_UPLOADED)
            r = await client.post(
                f"/api/servers/{sid}/attestations",
                **_att_upload(
                    _fake_pdf(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_auth(admin_token),
            )
            assert r.status_code >= 400
            assert await _count_action(pool, AUDIT_ATTESTATION_UPLOADED) == before
            # The document must roll back too, proving shared-transaction coupling.
            pool_check = await get_pool()
            async with pool_check.acquire() as conn:
                files = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", sid
                )
            assert files == 0
        finally:
            await _drop_servers([sid])

    async def test_upload_missing_qualification_creates_no_audit(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("anoqual")
        try:
            before = await _count_action(pool, AUDIT_ATTESTATION_UPLOADED)
            r = await client.post(
                f"/api/servers/{sid}/attestations",
                files=_upload(_pdf_bytes(), "c.pdf", "application/pdf"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 422
            assert await _count_action(pool, AUDIT_ATTESTATION_UPLOADED) == before
        finally:
            await _drop_servers([sid])

    async def test_upload_audit_detail_is_metadata_only(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("ameta")
        try:
            await self._upload(client, admin_token, sid)
            row = await _latest_action(pool, AUDIT_ATTESTATION_UPLOADED)
            _assert_no_sensitive(row["detail"])
            assert set(row["detail"]) == {
                "server_id",
                "attestation_id",
                "file_id",
                "qualification_name",
                "mime_type",
                "file_size",
                "status",
            }
        finally:
            await _drop_servers([sid])


# ------------------------------------------------------ 3. actor and target


class TestActorAndTargetSemantics:
    async def test_actor_is_the_authenticated_admin(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("aactor")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            assert row["actor_user_id"] == await _admin_id()
        finally:
            await _drop_servers([sid])

    async def test_actor_is_the_authenticated_manager(
        self, client: AsyncClient, pool, manager_token
    ):
        sid = await _new_server("amgr")
        try:
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(manager_token),
            )
            assert r.status_code == 201, r.text
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            # Different actor from the admin upload, so the Manager is recorded.
            assert row["actor_user_id"] != await _admin_id()
            assert row["actor_user_id"] is not None
        finally:
            await _drop_servers([sid])

    async def test_target_user_id_stays_null_for_all_server_actions(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("atarget")
        try:
            att_resp = await client.post(
                f"/api/servers/{sid}/attestations",
                **_att_upload(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_auth(admin_token),
            )
            att = att_resp.json()
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            await client.delete(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/verify",
                headers=_auth(admin_token),
            )
            for action in SERVER_AUDIT_ACTIONS:
                row = await _latest_action(pool, action)
                assert row is not None, f"{action} not recorded"
                assert row["target_user_id"] is None, (
                    f"{action} must keep target_user_id NULL"
                )
        finally:
            await _drop_servers([sid])

    async def test_server_id_present_in_detail_and_no_server_id_in_target(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("asid")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            row = await _latest_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            assert row["detail"]["server_id"] == sid
            assert row["target_user_id"] != sid
        finally:
            await _drop_servers([sid])


# ------------------------------------------------- 4. transaction consistency


class TestTransactionConsistency:
    async def test_successful_mutation_and_audit_commit_together(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("atxn")
        try:
            before = await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 201
            assert await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED) == before + 1
            # The photo really is stored, so both effects are durable.
            async with pool.acquire() as conn:
                files = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", sid
                )
            assert files == 1
        finally:
            await _drop_servers([sid])

    async def test_attestation_upload_commits_document_and_audit_together(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("atxn2")
        try:
            before = await _count_action(pool, AUDIT_ATTESTATION_UPLOADED)
            r = await client.post(
                f"/api/servers/{sid}/attestations",
                **_att_upload(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_auth(admin_token),
            )
            assert r.status_code == 201
            assert await _count_action(pool, AUDIT_ATTESTATION_UPLOADED) == before + 1
            async with pool.acquire() as conn:
                files = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", sid
                )
                atts = await conn.fetchval(
                    "SELECT count(*) FROM server_attestations WHERE server_id = $1", sid
                )
            assert files == 1
            assert atts == 1
        finally:
            await _drop_servers([sid])

    async def test_failed_transition_leaves_audit_count_unchanged(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("atxn3")
        try:
            r = await client.post(
                f"/api/servers/{sid}/attestations",
                **_att_upload(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_auth(admin_token),
            )
            att = r.json()
            await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/verify",
                headers=_auth(admin_token),
            )
            before = await _count_action(pool, AUDIT_ATTESTATION_SUPERSEDED)
            bad = await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/supersede",
                json={"superseded_by_id": str(uuid.uuid4())},
                headers=_auth(admin_token),
            )
            assert bad.status_code == 404
            assert await _count_action(pool, AUDIT_ATTESTATION_SUPERSEDED) == before
            # Status untouched, so no audit row can be claiming otherwise.
            async with pool.acquire() as conn:
                status = await conn.fetchval(
                    "SELECT status FROM server_attestations WHERE id = $1", att["id"]
                )
            assert status == "VERIFIED"
        finally:
            await _drop_servers([sid])


# ----------------------------------------------------------- 5. authorization


class TestAuthorizationEnforced:
    async def test_unauthenticated_cannot_upload_photo(self, client: AsyncClient):
        sid = await _new_server("aunauth")
        try:
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
            )
            assert r.status_code == 401
        finally:
            await _drop_servers([sid])

    async def test_unauthenticated_cannot_upload_attestation(self, client: AsyncClient):
        sid = await _new_server("aunauth2")
        try:
            r = await client.post(
                f"/api/servers/{sid}/attestations",
                **_att_upload(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
            )
            assert r.status_code == 401
        finally:
            await _drop_servers([sid])

    async def test_staff_cannot_mutate_photo(
        self, client: AsyncClient, pool, staff_token
    ):
        sid = await _new_server("astaff")
        try:
            before = await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED)
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(staff_token),
            )
            assert r.status_code == 403
            assert await _count_action(pool, AUDIT_PROFILE_PHOTO_UPLOADED) == before
        finally:
            await _drop_servers([sid])

    async def test_staff_cannot_mutate_attestation(
        self, client: AsyncClient, pool, staff_token
    ):
        sid = await _new_server("astaff2")
        try:
            before = await _count_action(pool, AUDIT_ATTESTATION_UPLOADED)
            r = await client.post(
                f"/api/servers/{sid}/attestations",
                **_att_upload(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_auth(staff_token),
            )
            assert r.status_code == 403
            assert await _count_action(pool, AUDIT_ATTESTATION_UPLOADED) == before
        finally:
            await _drop_servers([sid])

    async def test_manager_can_verify_attestation(
        self, client: AsyncClient, pool, manager_token
    ):
        sid = await _new_server("amgrverify")
        try:
            r = await client.post(
                f"/api/servers/{sid}/attestations",
                **_att_upload(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_auth(manager_token),
            )
            att = r.json()
            v = await client.patch(
                f"/api/servers/{sid}/attestations/{att['id']}/verify",
                headers=_auth(manager_token),
            )
            assert v.status_code == 200, v.text
            row = await _latest_action(pool, AUDIT_ATTESTATION_VERIFIED)
            assert row is not None
        finally:
            await _drop_servers([sid])

    async def test_admin_can_delete_photo(self, client: AsyncClient, pool, admin_token):
        sid = await _new_server("admdel")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            r = await client.delete(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert r.status_code == 200
            assert await _latest_action(pool, AUDIT_PROFILE_PHOTO_DELETED) is not None
        finally:
            await _drop_servers([sid])


# ------------------------------------------- 6. server events reach the API


class TestServerEventsVisibleToAdmins:
    async def test_admin_can_list_server_actions(
        self, client: AsyncClient, pool, admin_token
    ):
        sid = await _new_server("avisible")
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_upload(_png_bytes(), "p.png", "image/png"),
                headers=_auth(admin_token),
            )
            r = await client.get(
                "/api/audit-log",
                # Filtering by action keeps this deterministic and exercises the
                # action filter with a server-side value.
                params={
                    "action": AUDIT_PROFILE_PHOTO_UPLOADED,
                    "page": 1,
                    "page_size": 100,
                },
                headers=_auth(admin_token),
            )
            assert r.status_code == 200, r.text
            items = r.json()["items"]
            match = next(
                (
                    i for i in items
                    if i["action"] == AUDIT_PROFILE_PHOTO_UPLOADED
                    and (i.get("detail") or {}).get("server_id") == sid
                ),
                None,
            )
            assert match is not None, "photo upload event not returned by the API"
            assert match["target_user_id"] is None
            assert match["actor_email"] is not None
        finally:
            await _drop_servers([sid])

    async def test_manager_cannot_read_the_audit_log(self, client: AsyncClient, manager_token):
        r = await client.get("/api/audit-log", headers=_auth(manager_token))
        assert r.status_code == 403
