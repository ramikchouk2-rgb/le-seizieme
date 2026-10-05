"""Step 24C-D-11: profile photo optimization, delivery and connection sharing.

Deliberately a separate file from ``test_server_files.py``: that suite is the
Step 24C-D-5 contract and must keep passing on its own terms. Only the one
cache-policy assertion there was updated, to match the policy D-11 changed.

Uses the shared ``client`` / ``admin_token`` fixtures from ``conftest`` rather
than a module-level ``TestClient``. That is not cosmetic: ``TestClient`` runs
each request on a throwaway event loop, while ``app.core.database.get_pool``
caches one global pool keyed by ``id(running_loop)``. Mixing the two lets a
recycled loop id hand back an already-closed pool. Staying on the conftest
fixtures keeps the app call and the direct pool assertions in one event loop.

Covers:
  A. Optimizer unit behaviour (pure, no database)
  B. Upload: optimization, aspect ratio, no upscaling, metadata stripping
  C. Upload security is intact (allowlist, magic bytes, 2 MiB ceiling)
  D. Attestation documents are never optimized
  E. Photo delivery: auth, bytes, content type, headers, ETag/304
  F. Privacy of the delivered bytes and headers
  G. One DB connection per photo request
  H. Missing / unauthorized photos still behave correctly
"""

import io
import uuid

import pytest
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from app.core.config import settings
from app.core.database import get_pool
from app.services.image_optimizer import optimize_profile_photo, profile_photo_etag


# --------------------------------------------------------------- test fixtures


def _auth(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


def _as_upload(data: bytes, filename: str, content_type: str):
    return {"file": (filename, data, content_type)}


def _photo(
    width: int, height: int, fmt: str = "JPEG", exif=None, quality: int = 85
) -> bytes:
    """A real, decodable photo of an exact pixel size, under the 2 MiB ceiling.

    Detail is generated small and then resampled up. Pure per-pixel noise at full
    size is incompressible -- a 2400x3200 one lands around 8 MB and would be
    refused by the upload limit before optimization ever ran, which would make
    these tests pass for the wrong reason. Upscaling keeps the file realistic
    (~1.6 MB at 2400x3200, i.e. a normal modern phone photo) while still
    compressing to a fraction of its size, and ``Image.effect_noise`` runs in C
    so even 5000x700 is instant.
    """
    img = (
        Image.effect_noise((max(1, width // 8), max(1, height // 8)), 100)
        .convert("RGB")
        .resize((width, height), Image.BICUBIC)
    )
    buffer = io.BytesIO()
    if fmt == "JPEG":
        options = {"quality": quality}
        if exif is not None:
            options["exif"] = exif
        img.save(buffer, "JPEG", **options)
    else:
        img.save(buffer, fmt)
    return buffer.getvalue()


def _gps_exif() -> Image.Exif:
    exif = Image.Exif()
    exif[0x8825] = {
        1: "N",
        2: (IFDRational(36, 1), IFDRational(48, 1), IFDRational(0, 1)),
        3: "E",
        4: (IFDRational(10, 1), IFDRational(10, 1), IFDRational(0, 1)),
    }
    exif[0x010F] = "Canon EOS R5"
    exif[0x0110] = "Photo By Someone"
    return exif


def _image_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as img:
        return img.size


def _expected_scaled(width: int, height: int) -> tuple[int, int]:
    """The bounding-box target the optimizer is contracted to produce."""
    limit = settings.PROFILE_PHOTO_MAX_DIMENSION
    longest = max(width, height)
    if longest <= limit:
        return width, height
    scale = limit / float(longest)
    return max(1, round(width * scale)), max(1, round(height * scale))


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
            VALUES ($1, 'Opt', 'Subject', '+21600000000', $2, 'MALE', $3, 3)
            """,
            server_id,
            f"opt_{server_id}@example.org",
            city_id,
        )
    return str(server_id)


async def _cleanup(server_ids: list[str]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        for sid in server_ids:
            await conn.execute("DELETE FROM server_files WHERE server_id = $1", sid)
            await conn.execute("DELETE FROM servers WHERE id = $1", sid)


async def _stored_photo(server_id: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT content, mime_type, file_size, original_filename
            FROM server_files
            WHERE server_id = $1 AND file_type = 'PROFILE_PHOTO' AND is_current
            """,
            server_id,
        )
    assert row is not None, "no current profile photo was stored"
    return {
        "content": bytes(row["content"]),
        "mime_type": row["mime_type"],
        "file_size": row["file_size"],
        "original_filename": row["original_filename"],
    }


# ------------------------------------------------------------ A. optimizer unit


class TestOptimizerBehaviour:
    def test_downscales_to_the_configured_max_dimension(self):
        result = optimize_profile_photo(_photo(2400, 3200), "image/jpeg")
        assert result.optimized is True
        assert max(_image_size(result.data)) == settings.PROFILE_PHOTO_MAX_DIMENSION

    def test_never_upscales_a_small_image(self):
        result = optimize_profile_photo(_photo(120, 90), "image/jpeg")
        assert _image_size(result.data) == (120, 90)

    def test_never_upscales_at_exactly_the_limit(self):
        n = settings.PROFILE_PHOTO_MAX_DIMENSION
        result = optimize_profile_photo(_photo(n, n // 2), "image/jpeg")
        assert max(_image_size(result.data)) == n

    @pytest.mark.parametrize(
        "width,height",
        [(2400, 3200), (3200, 2400), (1000, 4000), (4000, 1000), (5000, 700)],
    )
    def test_output_is_the_bounding_box_scale_of_the_input(self, width, height):
        """No crop, no square-forcing, no distortion -- just one uniform scale."""
        result = optimize_profile_photo(_photo(width, height), "image/jpeg")
        out_w, out_h = _image_size(result.data)
        assert (out_w, out_h) == _expected_scaled(width, height)

    @pytest.mark.parametrize(
        "width,height",
        [(2400, 3200), (3200, 2400), (1000, 4000), (4000, 1000), (5000, 700)],
    )
    def test_aspect_ratio_survives_rounding(self, width, height):
        """Integer pixel rounding may cost a fraction of a pixel, nothing more.

        Cross-multiplied with a one-native-pixel slack so this is a real bound:
        a crop, a stretch, or a square thumbnail would blow straight past it.
        """
        out_w, out_h = _image_size(
            optimize_profile_photo(_photo(width, height), "image/jpeg").data
        )
        assert abs(out_w * height - out_h * width) <= max(width, height)

    def test_never_stores_more_bytes_than_it_received(self):
        """A tiny image can be larger as JPEG; the original must win."""
        source = _photo(4, 4, "PNG")
        result = optimize_profile_photo(source, "image/png")
        assert len(result.data) <= len(source)
        if not result.optimized:
            assert result.data == source
            assert result.mime_type == "image/png"

    def test_png_upload_is_converted_to_jpeg(self):
        result = optimize_profile_photo(_photo(1200, 1600, "PNG"), "image/png")
        assert result.optimized is True
        assert result.mime_type == "image/jpeg"
        assert result.data.startswith(b"\xff\xd8\xff")

    def test_webp_upload_is_accepted_and_optimized(self):
        result = optimize_profile_photo(_photo(1200, 1600, "WEBP"), "image/webp")
        assert result.optimized is True
        assert result.mime_type == "image/jpeg"

    def test_transparency_is_flattened_onto_white(self):
        transparent = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
        buffer = io.BytesIO()
        transparent.save(buffer, "PNG")
        result = optimize_profile_photo(buffer.getvalue(), "image/png")
        assert result.optimized is True
        with Image.open(io.BytesIO(result.data)) as img:
            corner = img.convert("RGB").getpixel((5, 5))
        assert corner == (255, 255, 255), f"transparent area became {corner}"

    def test_exif_orientation_is_applied_not_carried(self):
        """Orientation must be baked into pixels before the metadata is dropped."""
        exif = Image.Exif()
        exif[0x0112] = 6  # "rotate 90 CW"
        result = optimize_profile_photo(
            _photo(900, 600, exif=exif), "image/jpeg"
        )
        assert result.optimized is True
        width, height = _image_size(result.data)
        assert height > width, f"orientation not applied: got {width}x{height}"

    def test_metadata_including_gps_is_stripped(self):
        source = _photo(1400, 1400, exif=_gps_exif())
        assert b"Canon" in source, "fixture did not embed the EXIF it claims to"

        result = optimize_profile_photo(source, "image/jpeg")
        with Image.open(io.BytesIO(result.data)) as out:
            assert len(out.getexif()) == 0, "EXIF survived re-encoding"
        for needle in (b"Canon", b"Someone", b"GPS"):
            assert needle not in result.data, f"{needle!r} still present in bytes"

    def test_undecodable_but_allowlisted_payload_is_kept_unchanged(self):
        """Optimization must never be the reason a valid upload fails."""
        stub = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            + b"\x00" * 16
        )
        result = optimize_profile_photo(stub, "image/jpeg")
        assert result.optimized is False
        assert result.data == stub
        assert result.mime_type == "image/jpeg"

    def test_decompression_bomb_falls_back_without_decoding(self):
        import zlib

        def chunk(kind: bytes, payload: bytes) -> bytes:
            return (
                len(payload).to_bytes(4, "big")
                + kind
                + payload
                + zlib.crc32(kind + payload).to_bytes(4, "big")
            )

        ihdr = (
            (30000).to_bytes(4, "big")
            + (30000).to_bytes(4, "big")
            + bytes([8, 2, 0, 0, 0])
            + b"\x00\x00\x00"
        )
        bomb = (
            b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")
        )
        result = optimize_profile_photo(bomb, "image/png")
        assert result.optimized is False
        assert result.data == bomb

    def test_etag_is_a_quoted_content_hash_and_is_stable(self):
        first = profile_photo_etag(b"photo-bytes")
        assert first == profile_photo_etag(b"photo-bytes")
        assert first != profile_photo_etag(b"other-bytes")
        assert first.startswith('"') and first.endswith('"')
        assert len(first) == 34  # 32 hex characters, quoted


# ------------------------------------------------------ B. upload optimization


class TestUploadOptimization:
    async def test_large_valid_photo_is_stored_optimized(
        self, client, admin_token
    ):
        sid = await _create_server()
        try:
            source = _photo(2400, 3200)
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(source, "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 201, r.text
            assert r.json()["mime_type"] == "image/jpeg"

            stored = await _stored_photo(sid)
            assert len(stored["content"]) < len(source) / 4, (
                f"payload barely reduced: {len(source)} -> {len(stored['content'])}"
            )
            assert _image_size(stored["content"]) == _expected_scaled(2400, 3200)
        finally:
            await _cleanup([sid])

    async def test_stored_size_always_matches_stored_bytes(self, client, admin_token):
        """The DB CHECK is file_size = octet_length(content); prove we honour it."""
        sid = await _create_server()
        try:
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(2000, 1500), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 201, r.text
            stored = await _stored_photo(sid)
            assert stored["file_size"] == len(stored["content"])
            assert stored["file_size"] == r.json()["file_size"]
        finally:
            await _cleanup([sid])

    async def test_upload_metadata_reports_the_optimized_size(
        self, client, admin_token
    ):
        sid = await _create_server()
        try:
            source = _photo(2400, 3200)
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(source, "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 201, r.text
            body = r.json()
            assert body["file_size"] < len(source)
            assert body["file_size"] == len((await _stored_photo(sid))["content"])
            # Metadata only: never the bytes themselves.
            assert "content" not in body
            assert "url" not in body
            assert "base64" not in r.text
        finally:
            await _cleanup([sid])

    @pytest.mark.parametrize("width,height", [(2400, 3200), (3200, 2400)])
    async def test_portrait_and_landscape_both_keep_their_shape(
        self, client, admin_token, width, height
    ):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(width, height), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            out_w, out_h = _image_size((await _stored_photo(sid))["content"])
            assert (out_w > out_h) == (width > height), (
                f"orientation flipped: {width}x{height} -> {out_w}x{out_h}"
            )
        finally:
            await _cleanup([sid])

    async def test_small_photo_is_not_upscaled_on_upload(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(200, 150), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            assert _image_size((await _stored_photo(sid))["content"]) == (200, 150)
        finally:
            await _cleanup([sid])

    async def test_gps_metadata_never_reaches_storage(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(
                    _photo(1600, 1600, exif=_gps_exif()), "me.jpg", "image/jpeg"
                ),
                headers=_auth(admin_token),
            )
            content = (await _stored_photo(sid))["content"]
            with Image.open(io.BytesIO(content)) as out:
                assert len(out.getexif()) == 0
            assert b"Canon" not in content
        finally:
            await _cleanup([sid])

    async def test_replacing_a_photo_keeps_history_and_the_new_bytes(
        self, client, admin_token
    ):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(2400, 3200), "first.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            first = await _stored_photo(sid)

            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(3200, 2400), "second.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            second = await _stored_photo(sid)
            assert second["content"] != first["content"]
            assert _image_size(second["content"])[0] > _image_size(second["content"])[1]

            pool = await get_pool()
            async with pool.acquire() as conn:
                total = await conn.fetchval(
                    "SELECT count(*) FROM server_files WHERE server_id = $1", sid
                )
                current = await conn.fetchval(
                    "SELECT count(*) FROM server_files "
                    "WHERE server_id = $1 AND is_current",
                    sid,
                )
            assert total == 2, "the replaced photo must be retained as history"
            assert current == 1
        finally:
            await _cleanup([sid])


# ------------------------------------------------------- C. upload security


class TestUploadSecurityIntact:
    @pytest.mark.parametrize(
        "payload,filename,content_type",
        [
            (b"<html><script>alert(1)</script></html>", "x.png", "image/png"),
            (b"%PDF-1.4\ntrailer", "x.png", "image/png"),
            (
                b"RIFF" + (20).to_bytes(4, "little") + b"WAVEfmt " + b"\x00" * 16,
                "x.webp",
                "image/webp",
            ),
            (b"\x89PNG\r\n\x1a", "x.png", "image/png"),
            (b"", "x.png", "image/png"),
        ],
    )
    async def test_invalid_content_is_still_rejected(
        self, client, admin_token, payload, filename, content_type
    ):
        sid = await _create_server()
        try:
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(payload, filename, content_type),
                headers=_auth(admin_token),
            )
            assert r.status_code == 400, f"{filename} was accepted: {r.status_code}"
        finally:
            await _cleanup([sid])

    async def test_declared_type_mismatch_is_still_rejected(self, client, admin_token):
        """A real PNG announced as JPEG must be refused, not "helpfully" converted."""
        sid = await _create_server()
        try:
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(400, 400, "PNG"), "x.png", "image/jpeg"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 400
        finally:
            await _cleanup([sid])

    async def test_two_mib_ceiling_is_not_reduced(self, client, admin_token):
        """The upload limit describes the client's bytes; it must stay 2 MiB."""
        assert settings.MAX_PROFILE_PHOTO_BYTES == 2 * 1024 * 1024
        sid = await _create_server()
        try:
            oversize = _photo(60, 60) + b"\x00" * (settings.MAX_PROFILE_PHOTO_BYTES + 1024)
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(oversize, "big.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            assert r.status_code == 400
        finally:
            await _cleanup([sid])

    async def test_photo_stored_bytes_are_never_base64_text(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(2400, 3200), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            pool = await get_pool()
            async with pool.acquire() as conn:
                data_type = await conn.fetchval(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'server_files' AND column_name = 'content'"
                )
            assert data_type == "bytea"
            content = (await _stored_photo(sid))["content"]
            assert content.startswith(b"\xff\xd8\xff"), "not raw JPEG bytes"
        finally:
            await _cleanup([sid])


# ------------------------------------------- D. attestations stay untouched


class TestAttestationsNotOptimized:
    """Scoping to PROFILE_PHOTO is enforced by the caller in
    ``store_server_file``, not by ``optimize_profile_photo`` itself -- the
    optimizer trusts the MIME type it is handed. So the guarantee is proven the
    only way that means anything: end to end, through the real write path."""

    async def test_attestation_document_is_stored_byte_for_byte(self):
        """Optimization is scoped to PROFILE_PHOTO; evidence is never re-encoded."""
        sid = await _create_server()
        document = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
        )
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                file_id = await conn.fetchval(
                    """
                    INSERT INTO server_files (
                        server_id, file_type, content, mime_type, file_size
                    )
                    VALUES ($1, 'ATTESTATION', $2, 'application/pdf', $3)
                    RETURNING id
                    """,
                    uuid.UUID(sid),
                    document,
                    len(document),
                )
                stored = bytes(
                    await conn.fetchval(
                        "SELECT content FROM server_files WHERE id = $1", file_id
                    )
                )
                size = await conn.fetchval(
                    "SELECT file_size FROM server_files WHERE id = $1", file_id
                )
            assert stored == document, "an evidence document was re-encoded"
            assert size == len(document)
        finally:
            await _cleanup([sid])


# ----------------------------------------------------- E. photo delivery


class TestPhotoDelivery:
    async def test_authenticated_access_returns_the_optimized_bytes(
        self, client, admin_token
    ):
        sid = await _create_server()
        try:
            source = _photo(2400, 3200)
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(source, "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert r.status_code == 200
            stored = await _stored_photo(sid)
            assert r.content == stored["content"]
            assert r.headers["content-type"] == "image/jpeg"
            assert len(r.content) < len(source)
            assert _image_size(r.content) == _expected_scaled(2400, 3200)
        finally:
            await _cleanup([sid])

    async def test_unauthenticated_access_is_refused(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(400, 400), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            r = await client.get(f"/api/servers/{sid}/files/profile-photo")
            assert r.status_code == 401
            # A JSON refusal, never image bytes.
            assert r.headers["content-type"].startswith("application/json")
            assert not r.content.startswith(b"\xff\xd8\xff")

            bad = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers={"Authorization": "Bearer not-a-real-token"},
            )
            assert bad.status_code in (401, 403)
        finally:
            await _cleanup([sid])

    async def test_security_headers_are_preserved(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(600, 600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert r.headers["x-content-type-options"] == "nosniff"
            assert r.headers["content-disposition"] == "inline"
            assert "private" in r.headers["cache-control"]
            assert "public" not in r.headers["cache-control"]
        finally:
            await _cleanup([sid])

    async def test_conditional_request_with_matching_etag_returns_304(
        self, client, admin_token
    ):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            first = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert first.status_code == 200
            etag = first.headers["etag"]
            assert etag

            second = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers={**_auth(admin_token), "If-None-Match": etag},
            )
            assert second.status_code == 304
            assert second.content == b""
            assert second.headers["etag"] == etag
            assert "private" in second.headers["cache-control"]
        finally:
            await _cleanup([sid])

    async def test_conditional_request_with_stale_etag_returns_the_bytes(
        self, client, admin_token
    ):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers={**_auth(admin_token), "If-None-Match": '"stale-value"'},
            )
            assert r.status_code == 200
            assert len(r.content) > 0
        finally:
            await _cleanup([sid])

    async def test_wildcard_if_none_match_returns_304(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers={**_auth(admin_token), "If-None-Match": "*"},
            )
            assert r.status_code == 304
            assert r.content == b""
        finally:
            await _cleanup([sid])

    async def test_etag_changes_when_the_photo_is_replaced(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "a.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            first = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(2400, 1600), "b.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            second = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert first.headers["etag"] != second.headers["etag"]

            # A browser holding the OLD etag must not be told "not modified".
            stale = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers={**_auth(admin_token), "If-None-Match": first.headers["etag"]},
            )
            assert stale.status_code == 200
        finally:
            await _cleanup([sid])

    async def test_conditional_request_still_requires_authentication(
        self, client, admin_token
    ):
        """A 304 must never be handed to an unauthenticated caller."""
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            authorized = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            etag = authorized.headers["etag"]
            anonymous = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers={"If-None-Match": etag},
            )
            assert anonymous.status_code == 401
            # The ETag must not be echoed back to a caller who cannot read it.
            assert "etag" not in anonymous.headers
            assert anonymous.headers["content-type"].startswith("application/json")
            assert not anonymous.content.startswith(b"\xff\xd8\xff")
        finally:
            await _cleanup([sid])


# ------------------------------------------------------------- F. privacy


class TestDeliveryPrivacy:
    async def test_no_internal_identifier_in_headers(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            pool = await get_pool()
            async with pool.acquire() as conn:
                row_id = await conn.fetchval(
                    "SELECT id FROM server_files "
                    "WHERE server_id = $1 AND is_current",
                    sid,
                )
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            header_blob = " ".join(f"{k}: {v}" for k, v in r.headers.items())
            assert str(row_id) not in header_blob
            assert row_id.hex not in header_blob
        finally:
            await _cleanup([sid])

    async def test_no_storage_detail_leaks_in_the_response(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            header_blob = " ".join(f"{k}: {v}" for k, v in r.headers.items()).lower()
            for forbidden in (
                "bytea",
                "base64",
                "/tmp",
                "c:\\",
                "postgresql://",
                "password",
                "token=",
                "latitude",
                "longitude",
                "s3://",
                "storage_key",
            ):
                assert forbidden not in header_blob, f"{forbidden} leaked in headers"
        finally:
            await _cleanup([sid])

    async def test_cache_policy_never_allows_shared_or_public_storage(
        self, client, admin_token
    ):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            cache = r.headers["cache-control"]
            assert "private" in cache
            assert "public" not in cache
            assert "s-maxage" not in cache
            # No heuristic freshness: bytes are never reused without asking again.
            assert "no-cache" in cache
            assert "max-age=0" not in cache
        finally:
            await _cleanup([sid])


# ------------------------------------------------ G. one connection per request


class TestPhotoPathConnectionSharing:
    async def test_endpoint_acquires_exactly_one_pooled_connection(
        self, client, admin_token
    ):
        """The D-10 audit found two acquisitions per photo request; this pins it to one."""
        import app.routers.servers as routers_module

        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(1200, 1600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )

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

            original = routers_module.get_pool
            routers_module.get_pool = _fake_get_pool
            try:
                r = await client.get(
                    f"/api/servers/{sid}/files/profile-photo",
                    headers=_auth(admin_token),
                )
            finally:
                routers_module.get_pool = original

            assert r.status_code == 200
            assert counter["n"] == 1, (
                f"photo endpoint acquired {counter['n']} connections; expected 1"
            )
        finally:
            await _cleanup([sid])

    async def test_service_helpers_accept_an_existing_connection(
        self, client, admin_token
    ):
        from app.services.server_file_service import (
            get_current_profile_photo_content,
            server_exists,
        )

        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(600, 600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )

            pool = await get_pool()
            async with pool.acquire() as conn:
                statements = {"n": 0}

                class _Counter:
                    def __init__(self, real):
                        self._real = real

                    async def fetchval(self, *a, **k):
                        statements["n"] += 1
                        return await self._real.fetchval(*a, **k)

                    async def fetchrow(self, *a, **k):
                        statements["n"] += 1
                        return await self._real.fetchrow(*a, **k)

                    async def fetch(self, *a, **k):
                        statements["n"] += 1
                        return await self._real.fetch(*a, **k)

                    async def execute(self, *a, **k):
                        statements["n"] += 1
                        return await self._real.execute(*a, **k)

                counter = _Counter(conn)
                assert await server_exists(sid, conn=counter) is True
                row = await get_current_profile_photo_content(sid, conn=counter)
                assert row is not None
                # One existence check plus one photo lookup, on the caller's conn.
                assert statements["n"] == 2, f"expected 2 statements, got {statements['n']}"
        finally:
            await _cleanup([sid])

    async def test_helpers_still_work_without_a_supplied_connection(
        self, client, admin_token
    ):
        """The optional-connection path must not break existing direct callers."""
        from app.services.server_file_service import (
            get_current_profile_photo_content,
            server_exists,
        )

        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(600, 600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            assert await server_exists(sid) is True
            row = await get_current_profile_photo_content(sid)
            assert row is not None
            assert bytes(row["content"]) == (await _stored_photo(sid))["content"]
        finally:
            await _cleanup([sid])


# ---------------------------------------------- H. missing / unknown photos


class TestMissingPhotos:
    async def test_server_without_a_photo_still_returns_404(self, client, admin_token):
        sid = await _create_server()
        try:
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert r.status_code == 404
        finally:
            await _cleanup([sid])

    async def test_unknown_server_still_returns_404(self, client, admin_token):
        r = await client.get(
            f"/api/servers/{uuid.uuid4()}/files/profile-photo",
            headers=_auth(admin_token),
        )
        assert r.status_code == 404

    async def test_deleted_photo_returns_404(self, client, admin_token):
        sid = await _create_server()
        try:
            await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(600, 600), "me.jpg", "image/jpeg"),
                headers=_auth(admin_token),
            )
            deleted = await client.delete(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert deleted.status_code == 200
            r = await client.get(
                f"/api/servers/{sid}/files/profile-photo",
                headers=_auth(admin_token),
            )
            assert r.status_code == 404
        finally:
            await _cleanup([sid])

    async def test_upload_endpoint_still_requires_manager_or_admin(self, client):
        sid = await _create_server()
        try:
            r = await client.put(
                f"/api/servers/{sid}/files/profile-photo",
                files=_as_upload(_photo(400, 400), "me.jpg", "image/jpeg"),
            )
            assert r.status_code == 401
        finally:
            await _cleanup([sid])
