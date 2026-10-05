"""Step 24C-D-5: server profile photo system.

Covers:
  A. Schema / model behavior (BYTEA, constraints, indexes, no fabricated rows)
  B. Content validation (magic bytes, size, emptiness, filename spoofing)
  C. Upload, replacement, retrieval, deletion
  D. Authorization (unauthenticated, wrong role, manager, admin)
  E. Privacy and response contracts (no BYTEA in list/detail, no GPS, no URL)
  F. SQL / filename safety
"""

import io
import uuid
import zlib

import pytest

from app.core.config import settings
from app.core.database import get_pool
from app.main import app
from app.models.servers import (
    ServerFileMetadataResponse,
    ServerListItem,
    ServerProfileResponse,
)
from app.services.server_file_service import (
    sanitize_filename,
    sniff_image_mime_type,
    validate_profile_photo,
)

client = pytest.importorskip("fastapi.testclient").TestClient(app)

ADMIN_EMAIL = "admin@le-seizieme.local"
ADMIN_PASSWORD = "SecurePassword123!"


# --------------------------------------------------------------- test images


def _png_bytes(width: int = 2, height: int = 2) -> bytes:
    """Build a structurally valid, non-trivial PNG by hand (no fixtures needed)."""

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
        + bytes([8, 2, 0, 0, 0])  # 8-bit RGB
        + b"\x00\x00\x00"
    )
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _jpeg_bytes() -> bytes:
    """Minimal JPEG: SOI + APP0/JFIF marker, enough for magic-byte sniffing."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + b"\x00" * 16
    )


def _webp_bytes() -> bytes:
    return b"RIFF" + (20).to_bytes(4, "little") + b"WEBPVP8 " + b"\x00" * 16


def _pdf_bytes() -> bytes:
    """Minimal byte-accurate PDF used by the ATTESTATION file-kind tests."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )


def _fake_riff() -> bytes:
    """RIFF container that is NOT webp -- must not be accepted as an image."""
    return b"RIFF" + (20).to_bytes(4, "little") + b"WAVEfmt " + b"\x00" * 16


def _admin_headers():
    r = client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _as_upload(data: bytes, filename: str, content_type: str):
    return {"file": (filename, io.BytesIO(data), content_type)}


async def _create_server(email: str | None = None) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
        server_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO servers (
                id, first_name, last_name, phone, email, gender, city_id, years_experience
            )
            VALUES ($1, 'Photo', 'Subject', '+21600000000', $2, 'MALE', $3, 3)
            """,
            server_id,
            email or f"photo_{server_id}@example.org",
            city_id,
        )
    return str(server_id)


async def _cleanup(server_ids: list[str]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        for sid in server_ids:
            await conn.execute("DELETE FROM server_files WHERE server_id = $1", sid)
            await conn.execute("DELETE FROM servers WHERE id = $1", sid)


# ------------------------------------------------------ A. schema and models


class TestSchemaAndModels:
    async def test_table_shape(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'server_files'"
            )
        cols = {r["column_name"]: r for r in rows}
        for required in (
            "id",
            "server_id",
            "file_type",
            "content",
            "mime_type",
            "original_filename",
            "file_size",
            "is_current",
            "created_at",
            "updated_at",
        ):
            assert required in cols, f"missing column {required}"
        assert cols["content"]["data_type"] == "bytea"

    async def test_no_public_url_or_gps_columns_exist(self):
        """The table must not carry a URL, a path, or any location column."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'server_files'"
            )
        names = {r["column_name"] for r in rows}
        for forbidden in (
            "url",
            "public_url",
            "signed_url",
            "path",
            "storage_key",
            "latitude",
            "longitude",
            "geo",
        ):
            assert forbidden not in names, f"server_files must not expose {forbidden}"

    async def test_current_uniqueness_applies_to_profile_photos_only(self):
        """Step 24C-D-6 narrowed this: attestation documents are append-only, so
        a server may hold several current documents. Only photos are unique."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            idx = await conn.fetchval(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'idx_server_files_unique_current_photo'"
            )
        assert idx is not None, "the photo-scoped unique index must exist"
        assert "UNIQUE" in idx.upper()
        assert "is_current" in idx
        assert "PROFILE_PHOTO" in idx

    async def test_several_current_attestation_files_are_allowed(self):
        """Guards the append-only invariant for attestation documents."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
            server_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO servers (
                    id, first_name, last_name, phone, email, gender, city_id, years_experience
                )
                VALUES ($1, 'A', 'B', '+21600000000', $2, 'MALE', $3, 1)
                """,
                server_id,
                f"multiatt_{server_id}@example.org",
                city_id,
            )
        try:
            for i in range(3):
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO server_files (server_id, file_type, content, mime_type, file_size)
                        VALUES ($1, 'ATTESTATION', $2, 'application/pdf', $3)
                        """,
                        server_id,
                        _pdf_bytes(),
                        len(_pdf_bytes()),
                    )
        finally:
            await _cleanup([str(server_id)])

    async def test_no_fabricated_rows_from_legacy_profile_photo(self):
        """The migration must not synthesize photos from servers.profile_photo."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            legacy_populated = await conn.fetchval(
                "SELECT count(*) FROM servers WHERE profile_photo IS NOT NULL"
            )
            files = await conn.fetchval("SELECT count(*) FROM server_files")
        if legacy_populated:
            assert files == 0, (
                "server_files rows must not be fabricated from servers.profile_photo"
            )

    async def test_metadata_response_model_has_no_bytes_or_url(self):
        fields = set(ServerFileMetadataResponse.model_fields)
        for forbidden in ("content", "data", "bytes", "url", "public_url", "path"):
            assert forbidden not in fields
        assert "mime_type" in fields
        assert "file_size" in fields

    async def test_list_and_detail_models_expose_only_metadata(self):
        list_fields = set(ServerListItem.model_fields)
        detail_fields = set(ServerProfileResponse.model_fields)
        assert "has_profile_photo" in list_fields
        assert "has_profile_photo" in detail_fields
        assert "profile_photo" in detail_fields
        for fields in (list_fields, detail_fields):
            assert "content" not in fields
            assert "photo_bytes" not in fields

    async def test_size_constraint_must_match_content_length(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
            server_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO servers (
                    id, first_name, last_name, phone, email, gender, city_id, years_experience
                )
                VALUES ($1, 'A', 'B', '+21600000000', $2, 'MALE', $3, 1)
                """,
                server_id,
                f"constraint_{server_id}@example.org",
                city_id,
            )
        try:
            with pytest.raises(Exception):
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO server_files (server_id, content, mime_type, file_size)
                        VALUES ($1, $2, 'image/png', 999999)
                        """,
                        server_id,
                        _png_bytes(),
                    )
        finally:
            await _cleanup([str(server_id)])

    async def test_empty_content_is_rejected_by_constraint(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            city_id = await conn.fetchval("SELECT id FROM cities LIMIT 1")
            server_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO servers (
                    id, first_name, last_name, phone, email, gender, city_id, years_experience
                )
                VALUES ($1, 'A', 'B', '+21600000000', $2, 'MALE', $3, 1)
                """,
                server_id,
                f"empty_{server_id}@example.org",
                city_id,
            )
        try:
            with pytest.raises(Exception):
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO server_files (server_id, content, mime_type, file_size)
                        VALUES ($1, $2, 'image/png', 1)
                        """,
                        server_id,
                        b"",
                    )
        finally:
            await _cleanup([str(server_id)])


# ------------------------------------------------------- B. content validation


class TestContentValidation:
    def test_recognises_real_signatures(self):
        assert sniff_image_mime_type(_png_bytes()) == "image/png"
        assert sniff_image_mime_type(_jpeg_bytes()) == "image/jpeg"
        assert sniff_image_mime_type(_webp_bytes()) == "image/webp"

    def test_rejects_non_images_and_spoofs(self):
        assert sniff_image_mime_type(b"<html><script>alert(1)</script></html>") is None
        assert sniff_image_mime_type(b"%PDF-1.4") is None
        assert sniff_image_mime_type(_fake_riff()) is None
        assert sniff_image_mime_type(b"\x89PNG\r\n\x1a") is None  # truncated signature

    def test_extension_is_not_trusted(self):
        """Content decides the type; a misleading declared type cannot promote a
        non-image, and a real image is still recognised as such."""
        # A real PNG is accepted and classified by its own bytes.
        assert validate_profile_photo(_png_bytes(), "image/png") == "image/png"
        assert validate_profile_photo(_png_bytes(), "") == "image/png"
        # Text content claiming to be an image is refused.
        with pytest.raises(Exception):
            validate_profile_photo(b"just text", "image/png")
        with pytest.raises(Exception):
            validate_profile_photo(b"just text", "image/jpeg")

    def test_declared_type_mismatch_is_rejected(self):
        with pytest.raises(Exception):
            validate_profile_photo(_png_bytes(), "image/jpeg")

    def test_empty_upload_rejected(self):
        with pytest.raises(Exception):
            validate_profile_photo(b"", "image/png")

    def test_oversized_upload_rejected(self):
        oversized = _png_bytes() + b"\x00" * (settings.MAX_PROFILE_PHOTO_BYTES + 1024)
        with pytest.raises(Exception):
            validate_profile_photo(oversized, "image/png")

    def test_limit_is_configured(self):
        assert settings.MAX_PROFILE_PHOTO_BYTES > 0

    def test_octet_stream_declaration_is_tolerated(self):
        """Browsers may send octet-stream; content is what decides."""
        assert validate_profile_photo(_png_bytes(), "application/octet-stream") == "image/png"

    def test_filename_sanitisation(self):
        assert sanitize_filename("photo.png") == "photo.png"
        assert "/" not in (sanitize_filename("a/b/c.png") or "")
        assert "\\" not in (sanitize_filename("a\\b\\c.png") or "")
        assert sanitize_filename("../../etc/passwd") is not None
        assert ".." not in (sanitize_filename("../../etc/passwd") or "")
        assert sanitize_filename(None) is None
        assert sanitize_filename("   ") is None
        assert len(sanitize_filename("x" * 500) or "") <= 255


# ------------------------------------------------- C. upload/retrieve/delete


class TestPhotoLifecycle:
    async def test_upload_returns_metadata_without_bytes(self):
        sid = await _create_server()
        try:
            r = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["mime_type"] == "image/png"
            assert body["file_size"] == len(_png_bytes())
            assert body["is_current"] is True
            assert "content" not in body
            assert "url" not in body
        finally:
            await _cleanup([sid])

    async def test_retrieval_returns_exact_bytes(self):
        sid = await _create_server()
        png = _png_bytes()
        try:
            client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(png, "me.png", "image/png"),
                headers=_admin_headers(),
            )
            r = client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            )
            assert r.status_code == 200, r.text
            assert r.content == png
            assert r.headers["content-type"] == "image/png"
            # Step 24C-D-11 replaced `private, no-store, max-age=0` with a
            # private conditional-request policy: the bytes may be kept by the
            # browser but must be revalidated before any reuse, so the
            # Authorization header is still required on every single request.
            assert "private" in r.headers["cache-control"]
            assert "public" not in r.headers["cache-control"]
            assert "no-cache" in r.headers["cache-control"]
            assert r.headers["x-content-type-options"] == "nosniff"
        finally:
            await _cleanup([sid])

    async def test_all_three_allowed_types_round_trip(self):
        for data, name, mime in (
            (_png_bytes(), "a.png", "image/png"),
            (_jpeg_bytes(), "b.jpg", "image/jpeg"),
            (_webp_bytes(), "c.webp", "image/webp"),
        ):
            sid = await _create_server()
            try:
                up = client.put(
                    f"/api/servers/{sid}/files/profile-photo",
                    files=_as_upload(data, name, mime),
                    headers=_admin_headers(),
                )
                assert up.status_code == 201, up.text
                assert up.json()["mime_type"] == mime
                got = client.get(
                    f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
                )
                assert got.content == data
            finally:
                await _cleanup([sid])

    async def test_replacement_keeps_history_and_single_current(self):
        sid = await _create_server()
        first, second = _png_bytes(width=3), _jpeg_bytes()
        try:
            r1 = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(first, "a.png", "image/png"),
                headers=_admin_headers(),
            )
            assert r1.status_code == 201
            r2 = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(second, "b.jpg", "image/jpeg"),
                headers=_admin_headers(),
            )
            assert r2.status_code == 201, r2.text
            assert r2.json()["id"] != r1.json()["id"]
            assert r2.json()["mime_type"] == "image/jpeg"

            pool = await get_pool()
            async with pool.acquire() as conn:
                total = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", sid
                )
                current = await conn.fetchval(
                    "SELECT count(*) FROM server_files "
                    "WHERE server_id = $1 AND is_current = TRUE",
                    sid,
                )
            assert total == 2, "replaced photo must be retained as history"
            assert current == 1, "exactly one current photo per server"

            got = client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            )
            assert got.content == second
        finally:
            await _cleanup([sid])

    async def test_delete_deactivates_and_hides_photo(self):
        sid = await _create_server()
        try:
            client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=_admin_headers(),
            )
            d = client.delete(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            )
            assert d.status_code == 200, d.text

            pool = await get_pool()
            async with pool.acquire() as conn:
                remaining = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", sid
                )
                current = await conn.fetchval(
                    "SELECT count(*) FROM server_files "
                    "WHERE server_id = $1 AND is_current = TRUE",
                    sid,
                )
            assert remaining == 1, "deleted photo is retained as history"
            assert current == 0

            got = client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            )
            assert got.status_code == 404
        finally:
            await _cleanup([sid])

    async def test_nonexistent_server_is_404_on_every_operation(self):
        missing = str(uuid.uuid4())
        headers = _admin_headers()
        up = client.put(
            f"/api/servers/{missing}/files/profile-photo",
            files=_as_upload(_png_bytes(), "me.png", "image/png"),
            headers=headers,
        )
        assert up.status_code == 404
        assert client.get(
            f"/api/servers/{missing}/files/profile-photo", headers=headers
        ).status_code == 404
        assert client.delete(
            f"/api/servers/{missing}/files/profile-photo", headers=headers
        ).status_code == 404

    async def test_inactive_server_can_still_hold_a_photo(self):
        sid = await _create_server()
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("UPDATE servers SET is_active = FALSE WHERE id = $1", sid)
            up = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=_admin_headers(),
            )
            assert up.status_code == 201, up.text
            get = client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            )
            assert get.status_code == 200
        finally:
            await _cleanup([sid])

    async def test_get_and_delete_without_photo_are_404(self):
        sid = await _create_server()
        try:
            assert client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            ).status_code == 404
            assert client.delete(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            ).status_code == 404
        finally:
            await _cleanup([sid])

    async def test_invalid_upload_via_api_is_400_and_stores_nothing(self):
        sid = await _create_server()
        try:
            for data, name, mime in (
                (b"<script>alert(1)</script>", "x.png", "image/png"),
                (b"%PDF-1.4", "x.png", "image/png"),
                (_fake_riff(), "x.webp", "image/webp"),
                (b"", "x.png", "image/png"),
                (_png_bytes(), "x.png", "image/gif"),
            ):
                r = client.put(
                    f"/api/servers/{sid}/files/profile-photo",
                    files=_as_upload(data, name, mime),
                    headers=_admin_headers(),
                )
                assert r.status_code == 400, f"{name}/{mime} -> {r.status_code}"

            pool = await get_pool()
            async with pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", sid
                )
            assert count == 0, "no rejected upload may be persisted"
        finally:
            await _cleanup([sid])

    async def test_oversized_upload_via_api_is_rejected(self):
        sid = await _create_server()
        oversized = _png_bytes() + b"\x00" * (settings.MAX_PROFILE_PHOTO_BYTES + 1024)
        try:
            r = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(oversized, "big.png", "image/png"),
                headers=_admin_headers(),
            )
            assert r.status_code == 400, r.text
        finally:
            await _cleanup([sid])


# ------------------------------------------------------------ D. authorization


class TestPhotoAuthorization:
    async def test_unauthenticated_is_rejected(self, staff_token):
        sid = await _create_server()
        try:
            put = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
            )
            assert put.status_code == 401, put.status_code
            get = client.get(f"/api/servers/{sid}/files/profile-photo")
            assert get.status_code == 401
            dele = client.delete(f"/api/servers/{sid}/files/profile-photo")
            assert dele.status_code == 401
        finally:
            await _cleanup([sid])

    async def test_staff_role_is_forbidden(self, staff_token):
        sid = await _create_server()
        headers = _bearer(staff_token)
        try:
            up = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=headers,
            )
            assert up.status_code == 403, up.status_code
            get = client.get(f"/api/servers/{sid}/files/profile-photo", headers=headers)
            assert get.status_code == 403, get.status_code
            dele = client.delete(f"/api/servers/{sid}/files/profile-photo", headers=headers)
            assert dele.status_code == 403, dele.status_code
        finally:
            await _cleanup([sid])

    async def test_staff_cannot_read_bytes_of_an_existing_photo(self, staff_token):
        sid = await _create_server()
        png = _png_bytes()
        try:
            client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(png, "me.png", "image/png"),
                headers=_admin_headers(),
            )
            r = client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_bearer(staff_token)
            )
            assert r.status_code == 403
            assert png not in r.content
        finally:
            await _cleanup([sid])

    async def test_manager_can_manage_photos(self, manager_token):
        sid = await _create_server()
        headers = _bearer(manager_token)
        png = _png_bytes()
        try:
            up = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(png, "me.png", "image/png"),
                headers=headers,
            )
            assert up.status_code == 201, up.text
            get = client.get(f"/api/servers/{sid}/files/profile-photo", headers=headers)
            assert get.status_code == 200
            assert get.content == png
            dele = client.delete(f"/api/servers/{sid}/files/profile-photo", headers=headers)
            assert dele.status_code == 200, dele.text
        finally:
            await _cleanup([sid])

    async def test_admin_can_manage_photos(self):
        sid = await _create_server()
        try:
            up = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=_admin_headers(),
            )
            assert up.status_code == 201, up.text
        finally:
            await _cleanup([sid])

    async def test_every_photo_route_is_role_protected(self):
        """No route serving or mutating photos may skip the role dependency."""
        photo_routes = [
            r for r in app.routes if "profile-photo" in getattr(r, "path", "")
        ]
        assert len(photo_routes) == 3, photo_routes
        for route in photo_routes:
            names: set[str] = set()
            # Decorator-level `dependencies=[...]` land on route.dependencies.
            for dep in getattr(route, "dependencies", []) or []:
                call = getattr(dep, "dependency", None)
                if call is not None and hasattr(call, "__name__"):
                    names.add(call.__name__)
            # Signature-level `Depends(...)` land on dependant.dependencies.
            for dep in getattr(getattr(route, "dependant", None), "dependencies", []):
                call = getattr(dep, "dependency", None)
                if call is not None and hasattr(call, "__name__"):
                    names.add(call.__name__)
            assert "require_manager_or_admin" in names, (
                f"{route.path} {route.methods} is not role-protected (deps={names})"
            )


# --------------------------------------------------- E. privacy / contracts


class TestPrivacyAndContracts:
    async def test_server_list_never_returns_photo_bytes(self):
        sid = await _create_server()
        png = _png_bytes()
        try:
            client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(png, "me.png", "image/png"),
                headers=_admin_headers(),
            )
            r = client.get("/api/servers?page_size=100", headers=_admin_headers())
            assert r.status_code == 200, r.text
            body = r.json()
            serialized = str(body)
            assert "has_profile_photo" in serialized
            assert "\"content\"" not in serialized
            assert "photo_url" not in serialized
            assert "base64" not in serialized
            target = [i for i in body["items"] if i["id"] == sid]
            assert target and target[0]["has_profile_photo"] is True
        finally:
            await _cleanup([sid])

    async def test_server_detail_returns_metadata_not_bytes(self):
        sid = await _create_server()
        png = _png_bytes()
        try:
            client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(png, "me.png", "image/png"),
                headers=_admin_headers(),
            )
            r = client.get(f"/api/servers/{sid}", headers=_admin_headers())
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["has_profile_photo"] is True
            meta = body["profile_photo"]
            assert meta["mime_type"] == "image/png"
            assert meta["file_size"] == len(png)
            assert "content" not in meta
            assert "url" not in meta
            # The stored PNG bytes must not appear anywhere in the response.
            assert b"\x89PNG\r\n\x1a\n" not in r.content
            assert "base64" not in str(body)
        finally:
            await _cleanup([sid])

    async def test_detail_reports_absent_photo(self):
        sid = await _create_server()
        try:
            r = client.get(f"/api/servers/{sid}", headers=_admin_headers())
            assert r.status_code == 200
            assert r.json()["has_profile_photo"] is False
            assert r.json()["profile_photo"] is None
        finally:
            await _cleanup([sid])

    async def test_list_flags_are_false_for_servers_without_photos(self):
        sid = await _create_server()
        try:
            r = client.get("/api/servers?page_size=100", headers=_admin_headers())
            target = [i for i in r.json()["items"] if i["id"] == sid]
            assert target and target[0]["has_profile_photo"] is False
        finally:
            await _cleanup([sid])

    async def test_photo_metadata_exposes_no_gps_or_location(self):
        sid = await _create_server()
        try:
            client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=_admin_headers(),
            )
            meta = client.get(f"/api/servers/{sid}", headers=_admin_headers()).json()[
                "profile_photo"
            ]
            for forbidden in ("latitude", "longitude", "location", "area", "city", "gps"):
                assert forbidden not in meta
        finally:
            await _cleanup([sid])

    async def test_no_public_url_is_generated(self):
        sid = await _create_server()
        try:
            up = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=_admin_headers(),
            )
            assert up.status_code == 201
            body = up.json()
            serialized = str(body).lower()
            for forbidden in ("http://", "https://", "s3", "/files/", "public_url", "signed"):
                assert forbidden not in serialized, f"{forbidden} leaked in upload response"

            detail = client.get(f"/api/servers/{sid}", headers=_admin_headers()).json()
            detail_text = str(detail).lower()
            for forbidden in ("http://", "https://", "public_url", "signed"):
                assert forbidden not in detail_text
        finally:
            await _cleanup([sid])

    async def test_photo_headers_do_not_offer_a_public_asset(self):
        sid = await _create_server()
        try:
            client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "me.png", "image/png"),
                headers=_admin_headers(),
            )
            r = client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            )
            assert "private" in r.headers["cache-control"]
            assert "public" not in r.headers["cache-control"]
        finally:
            await _cleanup([sid])


# ------------------------------------------------------- F. injection / safety


class TestSqlAndFilenameSafety:
    async def test_injection_style_filename_is_stored_safely(self):
        sid = await _create_server()
        nasty = "'; DROP TABLE servers;--.png"
        try:
            r = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), nasty, "image/png"),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            stored = r.json()["original_filename"]
            # Stored as inert data: no quote, no SQL separator, no path.
            assert "'" not in stored
            assert ";" not in stored
            assert "/" not in stored

            # Table must still exist and be queryable.
            still_there = client.get("/api/servers?page_size=1", headers=_admin_headers())
            assert still_there.status_code == 200
        finally:
            await _cleanup([sid])

    async def test_path_traversal_filename_is_stored_as_basename(self):
        sid = await _create_server()
        try:
            r = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), "../../../etc/passwd", "image/png"),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            stored = r.json()["original_filename"]
            assert "/" not in stored
            assert "\\" not in stored
        finally:
            await _cleanup([sid])

    async def test_long_filename_is_capped(self):
        sid = await _create_server()
        try:
            r = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_png_bytes(), ("a" * 300) + ".png", "image/png"),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            assert len(r.json()["original_filename"]) <= 255
        finally:
            await _cleanup([sid])

    async def test_file_size_is_derived_from_stored_bytes(self):
        sid = await _create_server()
        data = _png_bytes(width=4, height=4)
        try:
            r = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(data, "me.png", "image/png"),
                headers=_admin_headers(),
            )
            assert r.json()["file_size"] == len(data)
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT file_size, octet_length(content) AS actual "
                    "FROM server_files WHERE server_id = $1 AND is_current = TRUE",
                    sid,
                )
            assert row["file_size"] == row["actual"] == len(data)
        finally:
            await _cleanup([sid])

    async def test_binary_payload_is_not_interpreted_as_sql(self):
        """Random bytes that happen to look like SQL text are still bytes."""
        sid = await _create_server()
        payload = _png_bytes() + b"'; DELETE FROM servers WHERE '1'='1"
        try:
            r = client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(payload, "me.png", "image/png"),
                headers=_admin_headers(),
            )
            assert r.status_code == 201, r.text
            assert client.get("/api/servers?page_size=1", headers=_admin_headers()).status_code == 200
            got = client.get(
                f"/api/servers/{sid}/files/profile-photo", headers=_admin_headers()
            )
            assert got.content == payload
        finally:
            await _cleanup([sid])