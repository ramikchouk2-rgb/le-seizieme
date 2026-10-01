"""Step 24C-D-6: professional attestations.

The business rule under test throughout: an attestation is NOT a verified
professional qualification until a Manager or Admin explicitly verifies it.
Uploading never verifies.
"""

import io
import uuid
import zlib

import pytest

from app.core.config import settings
from app.core.database import get_pool
from app.main import app
from app.services.server_attestation_service import (
    ALLOWED_TRANSITIONS,
    REPLACEMENT_REQUIRED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
    STATUS_VERIFIED,
)
from app.services.server_file_service import (
    ALLOWED_ATTESTATION_MIME_TYPES,
    sanitize_filename,
    sniff_mime_type,
    validate_attestation_document,
)

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"


# --------------------------------------------------------------- test files


def _png_bytes(width: int = 2, height: int = 2) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            len(payload).to_bytes(4, "big")
            + kind
            + payload
            + zlib.crc32(kind + payload).to_bytes(4, "big")
        )

    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes([8, 2, 0, 0, 0])
        + b"\x00\x00\x00"
    )
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _pdf_bytes() -> bytes:
    """A byte-accurate minimal PDF: header, catalog, pages, xref, trailer."""
    body = (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>\nendobj\n"
    )
    return b"%PDF-1.4\n" + body + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"


def _fake_pdf() -> bytes:
    """Starts with the PDF marker but has no version -- must not be accepted."""
    return b"%PDF-notreally\n" + b"\x00" * 32


def _elf_binary() -> bytes:
    """A real binary format (ELF) that must be rejected outright."""
    return b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 64


def _zip_bytes() -> bytes:
    """Archive: allowed nowhere in a conservative document allowlist."""
    return b"PK\x03\x04" + b"\x14\x00\x00\x00" + b"\x00" * 40


def _admin_headers():
    r = client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _as_upload(data: bytes, filename: str, content_type: str):
    """kwargs for a document-only multipart upload."""
    return {"file": (filename, io.BytesIO(data), content_type)}


def att_request(data: bytes, filename: str, content_type: str, **fields):
    """Kwargs for a multipart upload with attestation metadata.

    The document goes in `files`; the metadata must go in `data`, because
    httpx encodes every value of `files` as a file part.
    """
    return {
        "files": {"file": (filename, io.BytesIO(data), content_type)},
        "data": {k: v for k, v in fields.items() if v is not None},
    }


async def _create_server() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        server_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO servers (
                id, first_name, last_name, phone, email, gender, city_id, years_experience
            )
            VALUES ($1, 'Att', 'Subject', '+21600000000', $2, 'MALE', $3, 4)
            """,
            server_id,
            f"att_{server_id}@example.org",
            city_id,
        )
    return str(server_id)


async def _cleanup(server_ids: list[str]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        for sid in server_ids:
            # ON DELETE RESTRICT blocks a plain servers delete, so unwind the
            # attestation -> file chain explicitly.
            await conn.execute(
                "UPDATE server_attestations SET superseded_by_id = NULL "
                "WHERE server_id = $1",
                sid,
            )
            await conn.execute(
                "DELETE FROM server_attestations WHERE server_id = $1", sid
            )
            await conn.execute("DELETE FROM server_files WHERE server_id = $1", sid)
            await conn.execute("DELETE FROM servers WHERE id = $1", sid)


async def _db_status(server_id: str, attestation_id: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return dict(
            await conn.fetchrow(
                """
                SELECT status, verified_at, verified_by, rejection_reason,
                       superseded_by_id
                FROM server_attestations
                WHERE id = $1 AND server_id = $2
                """,
                attestation_id,
                server_id,
            )
        )


# ---------------------------------------------------------------- 1. schema


class TestAttestationSchema:
    async def test_table_and_columns_exist(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'server_attestations'"
            )
        cols = {r["column_name"]: r["data_type"] for r in rows}
        for required in (
            "id",
            "server_id",
            "file_id",
            "status",
            "qualification_name",
            "issuing_organization",
            "issued_on",
            "expires_on",
            "rejection_reason",
            "verified_at",
            "verified_by",
            "superseded_by_id",
            "created_at",
            "updated_at",
        ):
            assert required in cols, f"missing column {required}"
        # Document bytes live in server_files, never duplicated here.
        assert "content" not in cols
        assert "url" not in cols

    async def test_no_location_columns(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'server_attestations'"
            )
        names = {r["column_name"] for r in rows}
        for forbidden in ("latitude", "longitude", "location", "geo", "area", "city_id"):
            assert forbidden not in names

    async def test_status_enum_has_exactly_four_values(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'attestation_status' ORDER BY e.enumsortorder
                """
            )
        assert [r["enumlabel"] for r in rows] == [
            "PENDING",
            "VERIFIED",
            "REJECTED",
            "SUPERSEDED",
        ]

    async def test_file_type_enum_includes_attestation(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'server_file_type' ORDER BY e.enumsortorder
                """
            )
        assert "ATTESTATION" in {r["enumlabel"] for r in rows}

    async def test_referenced_indexes_exist(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'server_attestations'"
            )
        names = {r["indexname"] for r in rows}
        for required in (
            "idx_server_attestations_server_id",
            "idx_server_attestations_status",
            "idx_server_attestations_file_id",
            "idx_server_attestations_verified_by",
        ):
            assert required in names, f"missing index {required}"

    async def test_verified_status_requires_verifier_and_timestamp(self):
        """The core business rule, enforced by the storage layer."""
        server_id = await _create_server()
        pool = await get_pool()
        async with pool.acquire() as conn:
            city = await conn.fetchval("SELECT id FROM cities LIMIT 1")
            await conn.execute(
                """
                INSERT INTO servers (id, first_name, last_name, phone, email, gender, city_id, years_experience)
                VALUES ($1,'X','Y','+21600', $2,'MALE',$3,1)
                """,
                uuid.uuid4(),
                f"constr_{uuid.uuid4()}@example.org",
                city,
            )
        try:
            async with pool.acquire() as conn:
                file_id = await conn.fetchval(
                    """
                    INSERT INTO server_files (server_id, file_type, content, mime_type, file_size)
                    VALUES ($1, 'ATTESTATION', $2, 'application/pdf', $3)
                    RETURNING id
                    """,
                    server_id,
                    _pdf_bytes(),
                    len(_pdf_bytes()),
                )
                # VERIFIED without verified_at/verified_by must be impossible.
                with pytest.raises(Exception):
                    await conn.execute(
                        """
                        INSERT INTO server_attestations (
                            server_id, file_id, status, qualification_name
                        ) VALUES ($1, $2, 'VERIFIED', 'Sommelier')
                        """,
                        server_id,
                        file_id,
                    )
                # REJECTED without a reason must be impossible.
                with pytest.raises(Exception):
                    await conn.execute(
                        """
                        INSERT INTO server_attestations (
                            server_id, file_id, status, qualification_name, rejection_reason
                        ) VALUES ($1, $2, 'REJECTED', 'Sommelier', '   ')
                        """,
                        server_id,
                        file_id,
                    )
                # A blank qualification name is refused.
                with pytest.raises(Exception):
                    await conn.execute(
                        """
                        INSERT INTO server_attestations (
                            server_id, file_id, qualification_name
                        ) VALUES ($1, $2, '   ')
                        """,
                        server_id,
                        file_id,
                    )
                # Expiry before issuance is refused.
                with pytest.raises(Exception):
                    await conn.execute(
                        """
                        INSERT INTO server_attestations (
                            server_id, file_id, qualification_name, issued_on, expires_on
                        ) VALUES ($1, $2, 'Sommelier', '2026-01-10', '2026-01-01')
                        """,
                        server_id,
                        file_id,
                    )
        finally:
            await _cleanup([server_id])

    async def test_expiry_before_issuance_rejected_by_api(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(),
                    "c.pdf",
                    "application/pdf",
                    qualification_name="Sommelier",
                    issued_on="2026-01-10",
                    expires_on="2026-01-01",
                ),
                headers=_admin_headers(),
            )
            assert r.status_code == 400, r.text
        finally:
            await _cleanup([server_id])

    async def test_no_orphan_attestation_without_a_file(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            orphans = await conn.fetchval(
                "SELECT count(*) FROM server_attestations a "
                "LEFT JOIN server_files f ON f.id = a.file_id WHERE f.id IS NULL"
            )
        assert orphans == 0


# ------------------------------------------------------- 2. upload / PENDING


class TestUploadAlwaysPending:
    async def test_upload_creates_pending_not_verified(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(),
                    "cert.pdf",
                    "application/pdf",
                    qualification_name="Sommelier certified",
                    issuing_organization="Hotel School",
                    issued_on="2025-01-15",
                    expires_on="2027-01-15",
                ),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["status"] == STATUS_PENDING
            assert body["counts_as_verified_qualification"] is False
            assert body["verified_at"] is None
            assert body["verified_by"] is None
            assert body["rejection_reason"] is None
            assert body["qualification_name"] == "Sommelier certified"
            assert body["issuing_organization"] == "Hotel School"
            assert body["file"]["mime_type"] == "application/pdf"
        finally:
            await _cleanup([server_id])

    async def test_upload_response_has_no_document_bytes_or_url(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            )
            assert r.status_code == 201
            body = r.json()
            assert "content" not in body
            assert "url" not in body
            assert "http" not in str(body).lower()
            assert "base64" not in str(body).lower()
            assert b"%PDF".decode() not in r.content.decode("latin-1")
        finally:
            await _cleanup([server_id])

    async def test_upload_never_auto_verifies_even_by_admin(self):
        server_id = await _create_server()
        try:
            client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            )
            items = client.get(
                f"/api/servers/{server_id}/attestations", headers=_admin_headers()
            ).json()
            assert items["verified_count"] == 0
            assert all(not i["counts_as_verified_qualification"] for i in items["items"])
        finally:
            await _cleanup([server_id])

    async def test_missing_qualification_name_is_rejected(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                files=_as_upload(_pdf_bytes(), "c.pdf", "application/pdf"),
                headers=_admin_headers(),
            )
            assert r.status_code == 422, r.text
        finally:
            await _cleanup([server_id])

    async def test_blank_qualification_name_is_rejected(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="   ",
                ),
                headers=_admin_headers(),
            )
            assert r.status_code == 422, r.text
        finally:
            await _cleanup([server_id])

    async def test_nonexistent_server_is_404(self):
        missing = str(uuid.uuid4())
        r = client.post(
            f"/api/servers/{missing}/attestations",
            **att_request(
                _pdf_bytes(), "c.pdf", "application/pdf",
                qualification_name="Sommelier",
            ),
            headers=_admin_headers(),
        )
        assert r.status_code == 404

    async def test_inactive_server_can_still_hold_an_attestation(self):
        server_id = await _create_server()
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE servers SET is_active = FALSE WHERE id = $1", server_id
                )
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
        finally:
            await _cleanup([server_id])


# --------------------------------------------------------- 3. file validation


class TestAttestationDocumentValidation:
    def test_allowed_types(self):
        assert ALLOWED_ATTESTATION_MIME_TYPES == frozenset(
            {"application/pdf", "image/jpeg", "image/png", "image/webp"}
        )

    def test_pdf_and_images_detected_by_content(self):
        assert sniff_mime_type(_pdf_bytes()) == "application/pdf"
        assert sniff_mime_type(_png_bytes()) == "image/png"

    def test_fake_pdf_header_is_not_a_pdf(self):
        assert sniff_mime_type(_fake_pdf()) is None
        with pytest.raises(Exception):
            validate_attestation_document(_fake_pdf(), "application/pdf")

    def test_elf_and_zip_are_rejected(self):
        for data in (_elf_binary(), _zip_bytes()):
            assert sniff_mime_type(data) is None
            with pytest.raises(Exception):
                validate_attestation_document(data, "application/octet-stream")

    def test_php_and_html_upload_cannot_masquerade(self):
        for payload in (
            b"<?php system($_GET['c']); ?>",
            b"<html><body><script>alert(1)</script></body></html>",
        ):
            with pytest.raises(Exception):
                validate_attestation_document(payload, "image/png")

    def test_declared_type_mismatch_rejected(self):
        with pytest.raises(Exception):
            validate_attestation_document(_pdf_bytes(), "image/png")

    def test_empty_and_oversized_rejected(self):
        with pytest.raises(Exception):
            validate_attestation_document(b"", "application/pdf")
        oversized = _pdf_bytes() + b"\x00" * (settings.MAX_ATTESTATION_BYTES + 1024)
        with pytest.raises(Exception):
            validate_attestation_document(oversized, "application/pdf")

    async def test_invalid_uploads_via_api_store_nothing(self):
        server_id = await _create_server()
        try:
            for data, name, mime in (
                (_elf_binary(), "x.pdf", "application/pdf"),
                (_zip_bytes(), "x.pdf", "application/pdf"),
                (b"<?php evil(); ?>", "x.png", "image/png"),
                (b"", "x.pdf", "application/pdf"),
                (_pdf_bytes(), "x.pdf", "image/png"),
            ):
                r = client.post(
                    f"/api/servers/{server_id}/attestations",
                    **att_request(
                        data, name, mime, qualification_name="Sommelier"
                    ),
                    headers=_admin_headers(),
                )
                assert r.status_code == 400, f"{name} -> {r.status_code} {r.text[:120]}"

            pool = await get_pool()
            async with pool.acquire() as conn:
                atts = await conn.fetchval(
                    "SELECT count(*) FROM server_attestations WHERE server_id = $1",
                    server_id,
                )
                files = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", server_id
                )
            assert atts == 0, "no rejected upload may create an attestation"
            assert files == 0, "no rejected upload may leave a stored document"
        finally:
            await _cleanup([server_id])

    async def test_unsafe_filename_is_sanitised(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(),
                    "../../../etc/passwd.pdf",
                    "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            stored = r.json()["file"]["original_filename"]
            assert "/" not in stored
            assert "\\" not in stored
            assert ".." not in stored
        finally:
            await _cleanup([server_id])


# ------------------------------------------------------------- 4. lifecycle


class TestLifecycle:
    async def _upload(self, server_id: str, name: str = "Sommelier") -> dict:
        r = client.post(
            f"/api/servers/{server_id}/attestations",
            **att_request(
                _pdf_bytes(), "c.pdf", "application/pdf", qualification_name=name
            ),
            headers=_admin_headers(),
        )
        assert r.status_code == 201, r.text
        return r.json()

    async def test_pending_to_verified_records_verifier_and_timestamp(self):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            headers = _admin_headers()
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                headers=headers,
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["status"] == STATUS_VERIFIED
            assert body["counts_as_verified_qualification"] is True
            assert body["verified_at"] is not None
            assert body["verified_by"] is not None
            assert body["rejection_reason"] is None

            db = await _db_status(server_id, att["id"])
            assert str(db["status"]) == STATUS_VERIFIED
            assert db["verified_at"] is not None
            assert str(db["verified_by"]) == body["verified_by"]
        finally:
            await _cleanup([server_id])

    async def test_verifier_is_the_authenticated_user_and_cannot_forge(self):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            forged_id = str(uuid.uuid4())
            # A caller cannot nominate somebody else: verified_by is not a body
            # field, so a supplied one is simply ignored.
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                json={"verified_by": forged_id},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            recorded = r.json()["verified_by"]
            assert recorded != forged_id, "verified_by must come from the token"
            assert recorded == await _admin_user_id()
        finally:
            await _cleanup([server_id])

    async def test_pending_to_rejected_requires_and_stores_reason(self):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/reject",
                json={"rejection_reason": "Document illisible"},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["status"] == STATUS_REJECTED
            assert body["rejection_reason"] == "Document illisible"
            assert body["counts_as_verified_qualification"] is False
            assert body["verified_at"] is None
            assert body["verified_by"] is None
        finally:
            await _cleanup([server_id])

    async def test_rejection_without_reason_is_rejected(self):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            for payload in ({}, {"rejection_reason": ""}, {"rejection_reason": "   "}):
                r = client.patch(
                    f"/api/servers/{server_id}/attestations/{att['id']}/reject",
                    json=payload,
                    headers=_admin_headers(),
                )
                assert r.status_code == 422, f"{payload} -> {r.status_code}"
        finally:
            await _cleanup([server_id])

    async def test_pending_to_superseded(self):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/supersede",
                json={},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["status"] == STATUS_SUPERSEDED
            assert body["counts_as_verified_qualification"] is False
        finally:
            await _cleanup([server_id])

    async def test_supersede_records_the_replacement_chain(self):
        server_id = await _create_server()
        try:
            first = await self._upload(server_id)
            second = await self._upload(server_id)
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{first['id']}/supersede",
                json={"superseded_by_id": second["id"]},
                headers=_admin_headers(),
            )
            assert r.status_code == 200, r.text
            assert r.json()["superseded_by_id"] == second["id"]
        finally:
            await _cleanup([server_id])

    async def test_superseded_can_be_hidden_from_the_list(self):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/supersede",
                json={},
                headers=_admin_headers(),
            )
            with_hidden = client.get(
                f"/api/servers/{server_id}/attestations", headers=_admin_headers()
            ).json()
            assert with_hidden["total"] == 1, "history is retained by default"
            without = client.get(
                f"/api/servers/{server_id}/attestations?include_superseded=false",
                headers=_admin_headers(),
            ).json()
            assert without["total"] == 0
        finally:
            await _cleanup([server_id])

    @pytest.mark.parametrize(
        "first,second",
        [
            (STATUS_VERIFIED, "reject"),
            (STATUS_VERIFIED, "verify"),
            (STATUS_REJECTED, "verify"),
            (STATUS_REJECTED, "reject"),
            (STATUS_SUPERSEDED, "verify"),
            (STATUS_SUPERSEDED, "reject"),
            (STATUS_SUPERSEDED, "supersede"),
            (STATUS_PENDING, "pending"),
        ],
    )
    async def test_invalid_transitions_are_rejected(self, first, second):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            headers = _admin_headers()
            if first == STATUS_VERIFIED:
                assert client.patch(
                    f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                    headers=headers,
                ).status_code == 200
            elif first == STATUS_REJECTED:
                assert client.patch(
                    f"/api/servers/{server_id}/attestations/{att['id']}/reject",
                    json={"rejection_reason": "non conforme"},
                    headers=headers,
                ).status_code == 200
            elif first == STATUS_SUPERSEDED:
                assert client.patch(
                    f"/api/servers/{server_id}/attestations/{att['id']}/supersede",
                    json={},
                    headers=headers,
                ).status_code == 200

            if second == "pending":
                # No endpoint exists to move anything back to PENDING.
                assert STATUS_PENDING not in ALLOWED_TRANSITIONS[first]
                return

            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/{second}",
                json={"rejection_reason": "non conforme"},
                headers=headers,
            )
            assert r.status_code == 409, f"{first}->{second} -> {r.status_code}"
        finally:
            await _cleanup([server_id])

    async def test_rejected_and_superseded_are_terminal(self):
        """Documents the deliberate absence of a revocation path."""
        for terminal in (STATUS_REJECTED, STATUS_SUPERSEDED):
            assert ALLOWED_TRANSITIONS[terminal] == frozenset()

    async def test_verified_can_only_be_replaced_never_revoked(self):
        """A verified qualification may be superseded by a newer document, but
        there is no edge back to PENDING or across to REJECTED, so it can never
        be silently revoked. Revocation would need its own documented decision.
        """
        assert ALLOWED_TRANSITIONS[STATUS_VERIFIED] == frozenset({STATUS_SUPERSEDED})
        assert STATUS_PENDING not in ALLOWED_TRANSITIONS[STATUS_VERIFIED]
        assert STATUS_REJECTED not in ALLOWED_TRANSITIONS[STATUS_VERIFIED]
        assert (STATUS_VERIFIED, STATUS_SUPERSEDED) in REPLACEMENT_REQUIRED

    async def test_only_pending_has_outgoing_transitions(self):
        assert STATUS_PENDING in ALLOWED_TRANSITIONS
        assert ALLOWED_TRANSITIONS[STATUS_PENDING] == frozenset(
            {STATUS_VERIFIED, STATUS_REJECTED, STATUS_SUPERSEDED}
        )


# -------------------------------------------------- 5. qualification counting


class TestVerifiedQualificationCounting:
    async def test_only_verified_counts(self):
        server_id = await _create_server()
        try:
            headers = _admin_headers()
            made = []
            for name in ("Pending one", "Verified one", "Rejected one", "Superseded one"):
                r = client.post(
                    f"/api/servers/{server_id}/attestations",
                    **att_request(
                        _pdf_bytes(), "c.pdf", "application/pdf", qualification_name=name
                    ),
                    headers=headers,
                )
                assert r.status_code == 201
                made.append(r.json())

            def patch(att_id, action, body=None):
                return client.patch(
                    f"/api/servers/{server_id}/attestations/{att_id}/{action}",
                    json=body or {},
                    headers=headers,
                )

            assert patch(made[1]["id"], "verify").status_code == 200
            assert patch(made[2]["id"], "reject", {"rejection_reason": "x"}).status_code == 200
            assert patch(made[3]["id"], "supersede").status_code == 200

            listing = client.get(
                f"/api/servers/{server_id}/attestations", headers=headers
            ).json()
            assert listing["verified_count"] == 1
            verified = [i for i in listing["items"] if i["counts_as_verified_qualification"]]
            assert len(verified) == 1
            assert verified[0]["qualification_name"] == "Verified one"

            # PENDING / REJECTED / SUPERSEDED must never be counted.
            for name in ("Pending one", "Rejected one", "Superseded one"):
                assert all(
                    i["qualification_name"] != name
                    for i in verified
                ), f"{name} must not count as verified"
        finally:
            await _cleanup([server_id])

    async def test_server_detail_and_list_expose_the_count(self):
        server_id = await _create_server()
        try:
            headers = _admin_headers()
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            )
            att = r.json()
            assert client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                headers=headers,
            ).status_code == 200

            detail = client.get(f"/api/servers/{server_id}", headers=headers).json()
            assert detail["verified_attestation_count"] == 1

            listing = client.get("/api/servers?page_size=100", headers=headers).json()
            target = [i for i in listing["items"] if i["id"] == server_id]
            assert target and target[0]["verified_attestation_count"] == 1
        finally:
            await _cleanup([server_id])

    async def test_pending_does_not_raise_the_count(self):
        server_id = await _create_server()
        try:
            client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            )
            detail = client.get(
                f"/api/servers/{server_id}", headers=_admin_headers()
            ).json()
            assert detail["verified_attestation_count"] == 0
        finally:
            await _cleanup([server_id])

    async def _staffing_rows(self, server_id):
        pool = await get_pool()
        async with pool.acquire() as conn:
            return [
                dict(r)
                for r in await conn.fetch(
                    "SELECT id, event_id, role, assignment_status, confirmed_at "
                    "FROM event_staff WHERE server_id = $1 "
                    "ORDER BY event_id, role",
                    server_id,
                )
            ]

    async def test_attestations_do_not_touch_staffing_data(self):
        """This step must not influence staffing or selection.

        `event_staff` holds no score column of its own, so the real assertion is
        that attesting a server creates and modifies no staffing row at all.
        """
        server_id = await _create_server()
        try:
            before = await self._staffing_rows(server_id)

            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            )
            att = r.json()
            client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                headers=_admin_headers(),
            )

            after = await self._staffing_rows(server_id)
            assert before == after
        finally:
            await _cleanup([server_id])

    async def test_scoring_weights_are_untouched_by_this_step(self):
        from app.utils.selection_utils import SCORING_WEIGHTS

        assert "attestation" not in " ".join(SCORING_WEIGHTS.keys()).lower()


# ------------------------------------------------------------ 6. authorization


class TestAttestationAuthorization:
    async def _upload(self, server_id: str) -> dict:
        r = client.post(
            f"/api/servers/{server_id}/attestations",
            **att_request(
                _pdf_bytes(), "c.pdf", "application/pdf", qualification_name="Sommelier"
            ),
            headers=_admin_headers(),
        )
        assert r.status_code == 201, r.text
        return r.json()

    async def test_unauthenticated_rejected_everywhere(self, staff_token):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            base = f"/api/servers/{server_id}/attestations"
            unauth = [
                client.get(base),
                client.get(f"{base}/{att['id']}"),
                client.get(f"{base}/{att['id']}/file"),
                client.post(
                    base,
                    **att_request(
                        _pdf_bytes(), "c.pdf", "application/pdf",
                        qualification_name="X",
                    ),
                ),
                client.patch(f"{base}/{att['id']}/verify"),
                client.patch(f"{base}/{att['id']}/reject", json={"rejection_reason": "x"}),
                client.patch(f"{base}/{att['id']}/supersede", json={}),
            ]
            for r in unauth:
                assert r.status_code == 401, r.status_code
        finally:
            await _cleanup([server_id])

    async def test_staff_cannot_manage_or_read(self, staff_token):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            headers = _bearer(staff_token)
            base = f"/api/servers/{server_id}/attestations"
            assert client.get(base, headers=headers).status_code == 403
            assert client.get(f"{base}/{att['id']}", headers=headers).status_code == 403
            assert client.get(f"{base}/{att['id']}/file", headers=headers).status_code == 403
            assert client.post(
                base,
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf", qualification_name="X"
                ),
                headers=headers,
            ).status_code == 403
            assert client.patch(
                f"{base}/{att['id']}/verify", headers=headers
            ).status_code == 403
            assert client.patch(
                f"{base}/{att['id']}/reject",
                json={"rejection_reason": "x"},
                headers=headers,
            ).status_code == 403
            assert client.patch(
                f"{base}/{att['id']}/supersede", json={}, headers=headers
            ).status_code == 403
        finally:
            await _cleanup([server_id])

    async def test_staff_cannot_read_document_bytes(self, staff_token):
        server_id = await _create_server()
        pdf = _pdf_bytes()
        try:
            att = await self._upload(server_id)
            r = client.get(
                f"/api/servers/{server_id}/attestations/{att['id']}/file",
                headers=_bearer(staff_token),
            )
            assert r.status_code == 403
            assert pdf not in r.content
        finally:
            await _cleanup([server_id])

    async def test_manager_can_manage(self, manager_token):
        server_id = await _create_server()
        headers = _bearer(manager_token)
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            )
            assert r.status_code == 201, r.text
            att = r.json()
            assert client.get(
                f"/api/servers/{server_id}/attestations", headers=headers
            ).status_code == 200
            assert client.get(
                f"/api/servers/{server_id}/attestations/{att['id']}/file",
                headers=headers,
            ).status_code == 200
            v = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                headers=headers,
            )
            assert v.status_code == 200, v.text
            assert v.json()["counts_as_verified_qualification"] is True
        finally:
            await _cleanup([server_id])

    async def test_admin_can_manage(self):
        server_id = await _create_server()
        try:
            att = await self._upload(server_id)
            assert client.get(
                f"/api/servers/{server_id}/attestations", headers=_admin_headers()
            ).status_code == 200
        finally:
            await _cleanup([server_id])

    async def test_every_attestation_route_is_role_protected(self):
        routes = [r for r in app.routes if "attestation" in getattr(r, "path", "")]
        assert len(routes) == 7, routes
        for route in routes:
            names: set[str] = set()
            for dep in getattr(route, "dependencies", []) or []:
                call = getattr(dep, "dependency", None)
                if call is not None and hasattr(call, "__name__"):
                    names.add(call.__name__)
            for dep in getattr(getattr(route, "dependant", None), "dependencies", []):
                call = getattr(dep, "dependency", None)
                if call is not None and hasattr(call, "__name__"):
                    names.add(call.__name__)
            assert "require_manager_or_admin" in names, (
                f"{route.path} {route.methods} unprotected (deps={names})"
            )


# ------------------------------------------------------------ 7. privacy / IO


class TestAttestationPrivacyAndDocuments:
    async def test_document_retrieval_returns_exact_bytes_with_private_headers(self):
        server_id = await _create_server()
        pdf = _pdf_bytes()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    pdf, "cert.pdf", "application/pdf", qualification_name="Sommelier"
                ),
                headers=_admin_headers(),
            )
            att = r.json()
            got = client.get(
                f"/api/servers/{server_id}/attestations/{att['id']}/file",
                headers=_admin_headers(),
            )
            assert got.status_code == 200
            assert got.content == pdf
            assert got.headers["content-type"] == "application/pdf"
            assert "private" in got.headers["cache-control"]
            assert "no-store" in got.headers["cache-control"]
            assert got.headers["x-content-type-options"] == "nosniff"
        finally:
            await _cleanup([server_id])

    async def test_server_responses_contain_no_document_bytes(self):
        server_id = await _create_server()
        pdf = _pdf_bytes()
        try:
            client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    pdf, "c.pdf", "application/pdf", qualification_name="Sommelier"
                ),
                headers=_admin_headers(),
            )
            headers = _admin_headers()
            detail = client.get(f"/api/servers/{server_id}", headers=headers)
            listing = client.get("/api/servers?page_size=100", headers=headers)
            atts = client.get(
                f"/api/servers/{server_id}/attestations", headers=headers
            )
            for response in (detail, listing, atts):
                text = response.content.decode("latin-1")
                assert "%PDF" not in text
                assert '"content"' not in text
                assert "http://" not in text
                assert "https://" not in text
        finally:
            await _cleanup([server_id])

    async def test_attestation_metadata_exposes_no_location(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            )
            body = r.json()
            for forbidden in ("latitude", "longitude", "location", "city", "area", "gps"):
                assert forbidden not in body
                assert forbidden not in body["file"]
        finally:
            await _cleanup([server_id])

    async def test_cross_server_attestation_access_is_denied(self):
        server_a = await _create_server()
        server_b = await _create_server()
        try:
            att = client.post(
                f"/api/servers/{server_a}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=_admin_headers(),
            ).json()

            # server_b's URL, server_a's attestation id: must not resolve.
            assert client.get(
                f"/api/servers/{server_b}/attestations/{att['id']}", headers=_admin_headers()
            ).status_code == 404
            file_resp = client.get(
                f"/api/servers/{server_b}/attestations/{att['id']}/file",
                headers=_admin_headers(),
            )
            assert file_resp.status_code == 404
            assert b"%PDF" not in file_resp.content
            assert client.patch(
                f"/api/servers/{server_b}/attestations/{att['id']}/verify",
                headers=_admin_headers(),
            ).status_code == 404
        finally:
            await _cleanup([server_a, server_b])

    async def test_unknown_attestation_id_is_404(self):
        server_id = await _create_server()
        try:
            base = f"/api/servers/{server_id}/attestations/{uuid.uuid4()}"
            headers = _admin_headers()
            assert client.get(base, headers=headers).status_code == 404
            assert client.get(f"{base}/file", headers=headers).status_code == 404
            assert client.patch(f"{base}/verify", headers=headers).status_code == 404
        finally:
            await _cleanup([server_id])

    async def test_attestation_list_for_unknown_server_is_404(self):
        r = client.get(
            f"/api/servers/{uuid.uuid4()}/attestations", headers=_admin_headers()
        )
        assert r.status_code == 404


# ------------------------------------------------- 8. history / consistency


class TestHistoryAndTransactionConsistency:
    async def test_uploading_a_new_document_never_deletes_the_old_record(self):
        server_id = await _create_server()
        try:
            headers = _admin_headers()
            ids = []
            for i in range(3):
                r = client.post(
                    f"/api/servers/{server_id}/attestations",
                    **att_request(
                        _pdf_bytes(), f"c{i}.pdf", "application/pdf",
                        qualification_name=f"Cert {i}",
                    ),
                    headers=headers,
                )
                assert r.status_code == 201
                ids.append(r.json()["id"])

            listing = client.get(
                f"/api/servers/{server_id}/attestations", headers=headers
            ).json()
            assert listing["total"] == 3
            assert {i["id"] for i in listing["items"]} == set(ids)

            pool = await get_pool()
            async with pool.acquire() as conn:
                files = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1 "
                    "AND file_type = 'ATTESTATION'",
                    server_id,
                )
            assert files == 3, "each document is retained"
        finally:
            await _cleanup([server_id])

    async def test_document_and_attestation_are_committed_together(self):
        """A failed attestation insert must roll its document back too.

        Proven by forcing a database-level failure AFTER the document insert: a
        qualification name longer than the column accepts. The service's own
        validation is bypassed by calling it directly, so the error can only
        come from the CHECK/column constraint inside the transaction.
        """
        from app.services.server_attestation_service import create_attestation

        server_id = await _create_server()
        try:
            with pytest.raises(Exception):
                await create_attestation(
                    server_id=server_id,
                    data=_pdf_bytes(),
                    declared_mime_type="application/pdf",
                    original_filename="c.pdf",
                    # VARCHAR(200) will refuse this.
                    qualification_name="X" * 400,
                )
            pool = await get_pool()
            async with pool.acquire() as conn:
                atts = await conn.fetchval(
                    "SELECT count(*) FROM server_attestations WHERE server_id = $1",
                    server_id,
                )
                files = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", server_id
                )
            assert atts == 0
            assert files == 0, "document must roll back with the attestation"
        finally:
            await _cleanup([server_id])

    async def test_rejected_document_still_retained_for_audit(self):
        server_id = await _create_server()
        try:
            headers = _admin_headers()
            att = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/reject",
                json={"rejection_reason": "Certificat expiré"},
                headers=headers,
            )
            got = client.get(
                f"/api/servers/{server_id}/attestations/{att['id']}/file",
                headers=headers,
            )
            assert got.status_code == 200, "rejected document is still auditable"
        finally:
            await _cleanup([server_id])

    async def test_superseded_row_retains_its_verification_audit(self):
        server_id = await _create_server()
        try:
            headers = _admin_headers()
            att = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            replacement = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c2.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                headers=headers,
            )
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/supersede",
                json={"superseded_by_id": replacement["id"]},
                headers=headers,
            )
            assert r.status_code == 200, r.text
            body = client.get(
                f"/api/servers/{server_id}/attestations/{att['id']}", headers=headers
            ).json()
            assert body["status"] == STATUS_SUPERSEDED
            assert body["counts_as_verified_qualification"] is False
            # Audit of who verified it, and when, is not erased.
            assert body["verified_at"] is not None
            assert body["verified_by"] is not None
            assert body["superseded_by_id"] == replacement["id"]
        finally:
            await _cleanup([server_id])

    async def test_superseding_a_verified_attestation_requires_a_replacement(self):
        """A verified qualification must not silently stop counting."""
        server_id = await _create_server()
        try:
            headers = _admin_headers()
            att = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                headers=headers,
            )
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/supersede",
                json={},
                headers=headers,
            )
            assert r.status_code == 400, r.text
            still = client.get(
                f"/api/servers/{server_id}/attestations/{att['id']}", headers=headers
            ).json()
            assert still["status"] == STATUS_VERIFIED
        finally:
            await _cleanup([server_id])

    async def test_supersede_rejects_a_replacement_from_another_server(self):
        server_id = await _create_server()
        other_id = await _create_server()
        try:
            headers = _admin_headers()
            att = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/verify",
                headers=headers,
            )
            foreign = client.post(
                f"/api/servers/{other_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            r = client.patch(
                f"/api/servers/{server_id}/attestations/{att['id']}/supersede",
                json={"superseded_by_id": foreign["id"]},
                headers=headers,
            )
            assert r.status_code == 404, r.text
        finally:
            await _cleanup([server_id, other_id])

    async def test_a_rejected_attestation_cannot_be_revived(self):
        """A re-submitted document must be a new row, not a resurrection."""
        server_id = await _create_server()
        try:
            headers = _admin_headers()
            first = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "a.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            client.patch(
                f"/api/servers/{server_id}/attestations/{first['id']}/reject",
                json={"rejection_reason": "illisible"},
                headers=headers,
            )
            second = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "b.pdf", "application/pdf",
                    qualification_name="Sommelier",
                ),
                headers=headers,
            ).json()
            assert second["id"] != first["id"]
            assert second["status"] == STATUS_PENDING
        finally:
            await _cleanup([server_id])

    async def test_injection_style_qualification_name_is_stored_as_data(self):
        server_id = await _create_server()
        try:
            r = client.post(
                f"/api/servers/{server_id}/attestations",
                **att_request(
                    _pdf_bytes(), "c.pdf", "application/pdf",
                    qualification_name="'; DELETE FROM servers; --",
                    issuing_organization="'; DROP TABLE servers; --",
                ),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            assert (
                client.get("/api/servers?page_size=1", headers=_admin_headers()).status_code
                == 200
            )
        finally:
            await _cleanup([server_id])


# ----------------------------------------------------------------- helpers


async def _admin_user_id() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return str(
            await conn.fetchval("SELECT id FROM users WHERE email = $1", ADMIN_EMAIL)
        )
