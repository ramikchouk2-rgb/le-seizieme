"""Step 24C-D-5: reusable server file storage service.
Step 24C-D-7: administrative photo actions are written to the existing audit log
inside the same transaction as the change, with an explicit metadata whitelist so
no bytes, location data or credential can ever reach the detail JSON.

Design constraints enforced here:

* Content is validated by **magic bytes**, never by the filename extension and
  never by trusting the client-declared Content-Type. A `.png` holding script or
  a `text/html` upload is rejected.
* No public URL is ever produced or stored. The only way to obtain bytes is the
  explicitly authorized photo endpoint.
* No GPS/location metadata is accepted, derived or persisted. A file record
  carries bytes plus descriptive metadata only.
* Replaced files are retained as history (`is_current = FALSE`) rather than
  deleted, so an accidental replacement is recoverable.
* Every query is parameterized; filenames are sanitized before they can reach a
  log line or a response body.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_pool
from app.core.config import settings
from app.services.audit_service import log_audit_action
from app.services.image_optimizer import optimize_profile_photo, profile_photo_etag

# Step 24C-D-7: audit actions for server-file administration. An upload that
# replaces an existing photo is still PROFILE_PHOTO_UPLOADED; the difference is
# carried by detail["replaced"] so the action list cannot drift.
AUDIT_PROFILE_PHOTO_UPLOADED = "PROFILE_PHOTO_UPLOADED"
AUDIT_PROFILE_PHOTO_DELETED = "PROFILE_PHOTO_DELETED"

# Image types accepted for a profile photo. Kept as an explicit allowlist; a
# new type is a deliberate code change, never a configuration side effect.
ALLOWED_PROFILE_PHOTO_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

# Step 24C-D-6: professional attestation documents. Conservative on purpose --
# PDF plus the three image formats already proven for photos. No Office formats,
# no archives, no "anything goes".
ALLOWED_ATTESTATION_MIME_TYPES: frozenset[str] = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/webp"}
)

# Leading magic-byte signatures per supported type.
_MAGIC_SIGNATURES: tuple[tuple[str, bytes], ...] = (
    ("image/jpeg", b"\xff\xd8\xff"),
    ("image/png", b"\x89PNG\r\n\x1a\n"),
    # WEBP is a RIFF container: "RIFF" ....size.... "WEBP"
    ("image/webp", b"RIFF"),
    # PDF: "%PDF-" then a version marker.
    ("application/pdf", b"%PDF-"),
)

# File kinds this service can store. The enum itself is extended by migration;
# this mapping keeps the Python side in step and makes each kind's accepted
# types and size limit explicit in one place.
FILE_KINDS: dict[str, dict[str, object]] = {
    "PROFILE_PHOTO": {
        "allowed_mime_types": ALLOWED_PROFILE_PHOTO_MIME_TYPES,
        "max_bytes_setting": "MAX_PROFILE_PHOTO_BYTES",
        "single_current_per_server": True,
    },
    "ATTESTATION": {
        "allowed_mime_types": ALLOWED_ATTESTATION_MIME_TYPES,
        "max_bytes_setting": "MAX_ATTESTATION_BYTES",
        # Attestation history is append-only, so several current files per
        # server are expected; uniqueness is enforced by the attestation row,
        # not by server_files.
        "single_current_per_server": False,
    },
}

_MAX_FILENAME_LENGTH = 255
_FILENAME_STRIP_RE = re.compile(r"[^A-Za-z0-9._-]+")
# Path separators and traversal markers are removed outright.
_FILENAME_UNSAFE_RE = re.compile(r"[\\/\x00]")

PROFILE_PHOTO_FILE_TYPE = "PROFILE_PHOTO"
ATTESTATION_FILE_TYPE = "ATTESTATION"


def max_bytes_for(file_type: str) -> int:
    """Size ceiling for a file kind, read from settings."""
    kind = FILE_KINDS.get(file_type)
    if kind is None:
        raise ValueError(f"Unsupported server file type: {file_type}")
    return int(getattr(settings, str(kind["max_bytes_setting"])))


def max_profile_photo_bytes() -> int:
    """Maximum accepted profile photo size in bytes."""
    return max_bytes_for(PROFILE_PHOTO_FILE_TYPE)


def max_attestation_bytes() -> int:
    """Maximum accepted attestation document size in bytes."""
    return max_bytes_for(ATTESTATION_FILE_TYPE)


def sanitize_filename(filename: str | None) -> str | None:
    """Reduce an uploaded filename to a safe, display-only basename.

    Strips any directory component so a caller cannot inject a path, removes
    control characters, and caps the length. The result is never used to build
    a filesystem path or a URL -- BYTEA storage means there is no path to build.
    """
    if filename is None:
        return None
    cleaned = _FILENAME_UNSAFE_RE.sub("", filename).strip()
    cleaned = _FILENAME_STRIP_RE.sub("_", cleaned)
    cleaned = cleaned.lstrip(".")
    if not cleaned:
        return None
    return cleaned[:_MAX_FILENAME_LENGTH]


def sniff_mime_type(data: bytes) -> str | None:
    """Return the MIME type implied by the leading bytes, or None.

    Step 24C-D-6: this is the single content-sniffing entry point, shared by
    photos and attestation documents so the two can never drift apart.
    """
    for mime_type, signature in _MAGIC_SIGNATURES:
        if not data.startswith(signature):
            continue
        if mime_type == "image/webp":
            # A bare "RIFF" prefix is not enough to claim WEBP.
            if len(data) >= 12 and data[8:12] == b"WEBP":
                return mime_type
            continue
        if mime_type == "application/pdf":
            # "%PDF-" must be followed by a version digit ("%PDF-1.4", "%PDF-2.0").
            # A file that merely starts with those bytes is not accepted.
            if len(data) >= 8 and data[5:6].isdigit():
                return mime_type
            continue
        return mime_type
    return None


def sniff_image_mime_type(data: bytes) -> str | None:
    """Return the MIME type implied by the leading bytes, or None."""
    sniffed = sniff_mime_type(data)
    if sniffed in ALLOWED_PROFILE_PHOTO_MIME_TYPES:
        return sniffed
    return None


def validate_file_content(
    data: bytes,
    declared_mime_type: str | None,
    file_type: str,
) -> str:
    """Validate bytes for a file kind and return the MIME type to persist.

    Raises HTTPException 400 on any validation failure. The declared MIME type
    is used only as a cross-check: it can reject a file but can never vouch for
    one.
    """
    kind = FILE_KINDS.get(file_type)
    if kind is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type de fichier serveur non pris en charge.",
        )
    allowed: frozenset[str] = kind["allowed_mime_types"]  # type: ignore[assignment]

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )

    size = len(data)
    limit = max_bytes_for(file_type)
    if size > limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le fichier est trop volumineux "
                f"({size} octets, maximum {limit} octets)."
            ),
        )

    sniffed = sniff_mime_type(data)
    if sniffed is None or sniffed not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Format de document non reconnu ou non autorisé. "
                f"Formats acceptés : {', '.join(sorted(allowed))}."
            ),
        )

    if declared_mime_type:
        normalized = declared_mime_type.split(";")[0].strip().lower()
        if (
            normalized
            and normalized != "application/octet-stream"
            and normalized != sniffed
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Le type déclaré ne correspond pas au contenu du fichier."
                ),
            )

    return sniffed


def validate_profile_photo(data: bytes, declared_mime_type: str | None) -> str:
    """Validate profile photo bytes and return the MIME type to persist."""
    return validate_file_content(data, declared_mime_type, PROFILE_PHOTO_FILE_TYPE)


def validate_attestation_document(
    data: bytes, declared_mime_type: str | None
) -> str:
    """Validate an attestation document and return the MIME type to persist."""
    return validate_file_content(data, declared_mime_type, ATTESTATION_FILE_TYPE)


def _metadata_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """Build the metadata projection. `content` is intentionally never read."""
    created_at = row["created_at"]
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {
        "id": str(row["id"]),
        "server_id": str(row["server_id"]),
        "file_type": str(row["file_type"]),
        "mime_type": row["mime_type"],
        "original_filename": row["original_filename"],
        "file_size": row["file_size"],
        "is_current": bool(row["is_current"]),
        "created_at": created_at,
    }


async def server_exists(server_id: str, conn=None) -> bool:
    """Whether a server id is known.

    Step 24C-D-11: accepts an existing connection so a caller that must both
    verify the server and read its photo can do so on ONE pooled connection
    instead of acquiring the pool twice for a single request.
    """

    async def _check(active_conn) -> bool:
        return bool(
            await active_conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM servers WHERE id = $1)", server_id
            )
        )

    if conn is not None:
        return await _check(conn)
    pool = await get_pool()
    async with pool.acquire() as owned:
        return await _check(owned)


async def get_current_file_metadata(
    server_id: str, file_type: str
) -> dict[str, Any] | None:
    """Metadata for a server's current file of a kind. Never selects BYTEA."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, server_id, file_type, mime_type, original_filename,
                   file_size, is_current, created_at
            FROM server_files
            WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
            ORDER BY created_at DESC
            LIMIT 1
            """,
            server_id,
            file_type,
        )
        return _metadata_from_row(dict(row)) if row else None


async def get_current_file_content(
    server_id: str, file_type: str, conn=None
) -> dict[str, Any] | None:
    """Bytes + MIME for the authorized retrieval endpoint of a given kind.

    Step 24C-D-6: for ATTESTATION files there may be several current files, so
    callers that need one specific document must pass an explicit file id. This
    helper exists for kinds with a single current file (profile photos).

    Step 24C-D-11: `conn` lets the photo endpoint reuse the connection it already
    holds for the server-exists check, so serving one photo costs ONE pool
    acquisition instead of two. When omitted, a connection is acquired as before.
    """
    query = """
        SELECT id, server_id, file_type, mime_type, original_filename,
               file_size, is_current, created_at, content
        FROM server_files
        WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
        ORDER BY created_at DESC
        LIMIT 1
    """

    async def _fetch(active_conn) -> dict[str, Any] | None:
        row = await active_conn.fetchrow(query, server_id, file_type)
        return dict(row) if row else None

    if conn is not None:
        return await _fetch(conn)
    pool = await get_pool()
    async with pool.acquire() as owned:
        return await _fetch(owned)


async def get_file_content_by_id(
    server_id: str, file_id: str, file_type: str
) -> dict[str, Any] | None:
    """Bytes + MIME for one specific file, scoped to its owning server.

    Scoping by BOTH server_id and file_id is what prevents a caller from
    reaching another server's document by guessing a file id.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, server_id, file_type, mime_type, original_filename,
                   file_size, is_current, created_at, content
            FROM server_files
            WHERE id = $1 AND server_id = $2 AND file_type = $3
            LIMIT 1
            """,
            file_id,
            server_id,
            file_type,
        )
        return dict(row) if row else None


async def get_file_metadata_by_id(
    server_id: str, file_id: str, file_type: str
) -> dict[str, Any] | None:
    """Metadata for one specific file, scoped to its owning server."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, server_id, file_type, mime_type, original_filename,
                   file_size, is_current, created_at
            FROM server_files
            WHERE id = $1 AND server_id = $2 AND file_type = $3
            LIMIT 1
            """,
            file_id,
            server_id,
            file_type,
        )
        return _metadata_from_row(dict(row)) if row else None


async def ensure_server_exists(conn, server_id: str) -> None:
    """Raise 404 when the server is unknown. Caller owns the transaction."""
    exists = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM servers WHERE id = $1)", server_id
    )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Serveur introuvable."
        )


async def store_server_file(
    conn,
    server_id: str,
    file_type: str,
    data: bytes,
    declared_mime_type: str | None,
    original_filename: str | None,
) -> dict[str, Any]:
    """Store one file of a kind, inside the caller's transaction.

    The caller owns the transaction so an attestation row and its document are
    committed atomically -- a document can never exist without its attestation,
    nor the reverse.

    For kinds flagged ``single_current_per_server`` the previous current file is
    deactivated (never deleted) so history survives a replacement.

    Step 24C-D-11: profile photos are optimized after validation and before they
    are persisted. Validation deliberately runs FIRST and on the ORIGINAL bytes,
    so the 2 MiB upload ceiling and the magic-byte allowlist still describe what
    the client actually sent and no previously valid upload starts failing.
    Only what gets stored shrinks. Attestation documents are NOT touched: they
    are evidence, and must be preserved byte-for-byte as submitted.
    """
    mime_type = validate_file_content(data, declared_mime_type, file_type)
    safe_filename = sanitize_filename(original_filename)
    kind = FILE_KINDS[file_type]

    if file_type == PROFILE_PHOTO_FILE_TYPE:
        optimized = optimize_profile_photo(data, mime_type)
        data = optimized.data
        mime_type = optimized.mime_type

    # Measured on the bytes actually persisted, so the
    # server_files_size_matches_content_check constraint always holds.
    file_size = len(data)

    if kind["single_current_per_server"]:
        await conn.execute(
            """
            UPDATE server_files
            SET is_current = FALSE, updated_at = NOW()
            WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
            """,
            server_id,
            file_type,
        )

    row = await conn.fetchrow(
        """
        INSERT INTO server_files (
            server_id, file_type, content, mime_type,
            original_filename, file_size, is_current
        )
        VALUES ($1, $2, $3, $4, $5, $6, TRUE)
        RETURNING id, server_id, file_type, mime_type, original_filename,
                  file_size, is_current, created_at
        """,
        server_id,
        file_type,
        data,
        mime_type,
        safe_filename,
        file_size,
    )
    return _metadata_from_row(dict(row))


# --------------------------------------------------------------------------
# Profile photo wrappers.
#
# Kept as the public surface for Step 24C-D-5 so the router and its tests are
# unaffected; the shared implementation lives in the helpers above.
# --------------------------------------------------------------------------


async def get_current_profile_photo_metadata(server_id: str) -> dict[str, Any] | None:
    """Metadata only. This is what detail responses use; no BYTEA is selected."""
    return await get_current_file_metadata(server_id, PROFILE_PHOTO_FILE_TYPE)


async def has_profile_photo(server_id: str) -> bool:
    metadata = await get_current_profile_photo_metadata(server_id)
    return metadata is not None


async def load_servers_with_profile_photo(
    server_ids: list[str], conn=None
) -> dict[str, bool]:
    """Batched boolean projection. Avoids an N+1 lookup on list endpoints.

    A boolean only: no bytes, no path, no URL. Consumers that need the image
    itself call the authenticated content endpoint for that one server.

    Step 24C-D-8B: `conn` lets a report path reuse its own connection instead of
    acquiring a second one from the pool.
    """
    if not server_ids:
        return {}

    async def _fetch(active_conn) -> dict[str, bool]:
        rows = await active_conn.fetch(
            """
            SELECT DISTINCT server_id
            FROM server_files
            WHERE server_id = ANY($1::uuid[])
              AND file_type = $2
              AND is_current = TRUE
            """,
            server_ids,
            PROFILE_PHOTO_FILE_TYPE,
        )
        with_photo = {str(r["server_id"]) for r in rows}
        return {sid: sid in with_photo for sid in server_ids}

    if conn is not None:
        return await _fetch(conn)
    pool = await get_pool()
    async with pool.acquire() as owned:
        return await _fetch(owned)


async def get_current_profile_photo_content(
    server_id: str, conn=None
) -> dict[str, Any] | None:
    """Bytes + MIME for the authorized photo endpoint only.

    Step 24C-D-11: pass `conn` to share the caller's connection with the
    server-exists check, so one photo request touches the pool once.
    """
    return await get_current_file_content(server_id, PROFILE_PHOTO_FILE_TYPE, conn=conn)


async def upload_profile_photo(
    server_id: str,
    data: bytes,
    declared_mime_type: str | None,
    original_filename: str | None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Upload or replace the current profile photo.

    Replacement deactivates the previous current file instead of deleting it, so
    history is preserved. The insert and the deactivation happen in one
    transaction, and the partial UNIQUE index on (server_id, file_type) scoped to
    file_type = 'PROFILE_PHOTO' WHERE is_current guarantees at most one current
    photo even under concurrent uploads.

    Step 24C-D-7: when `actor_id` is given, a PROFILE_PHOTO_UPLOADED audit row is
    written INSIDE the same transaction, so a rolled-back upload can never leave a
    misleading record behind. Whether the upload replaced an existing photo is
    captured as `replaced` rather than as a separate action.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await ensure_server_exists(conn, server_id)

            # Read the prior state before store_server_file deactivates it, so
            # "replaced" reflects what actually happened.
            previous = await conn.fetchrow(
                """
                SELECT id FROM server_files
                WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
                """,
                server_id,
                PROFILE_PHOTO_FILE_TYPE,
            )
            replaced = previous is not None

            metadata = await store_server_file(
                conn,
                server_id,
                PROFILE_PHOTO_FILE_TYPE,
                data,
                declared_mime_type,
                original_filename,
            )

            if actor_id:
                # Explicit whitelist. `metadata` is already a metadata projection
                # with no `content` key, but the keys are still named one by one
                # so a future change to that projection cannot silently start
                # writing bytes into the audit log.
                await log_audit_action(
                    conn,
                    actor_id,
                    AUDIT_PROFILE_PHOTO_UPLOADED,
                    {
                        "server_id": str(server_id),
                        "file_id": str(metadata["id"]),
                        "mime_type": str(metadata["mime_type"]),
                        "file_size": int(metadata["file_size"]),
                        "replaced": replaced,
                    },
                    target_id=None,
                )
            return metadata


async def delete_current_profile_photo(
    server_id: str, actor_id: str | None = None
) -> bool:
    """Deactivate the current profile photo.

    Returns True when a photo was removed. The row is retained as history
    (`is_current = FALSE`) rather than hard-deleted, so the operation is
    reversible and audit-friendly.

    Step 24C-D-7: the deactivation and its PROFILE_PHOTO_DELETED audit row now
    share ONE explicit transaction. Previously this was a bare autocommitted
    UPDATE, which would have let an audit row commit independently of the change
    it described. When there is no current photo the function still returns False
    and writes no audit row, so a no-op cannot look like a deletion.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                """
                UPDATE server_files
                SET is_current = FALSE, updated_at = NOW()
                WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
                RETURNING id, mime_type, file_size
                """,
                server_id,
                PROFILE_PHOTO_FILE_TYPE,
            )
            if rows and actor_id:
                for row in rows:
                    await log_audit_action(
                        conn,
                        actor_id,
                        AUDIT_PROFILE_PHOTO_DELETED,
                        {
                            "server_id": str(server_id),
                            "file_id": str(row["id"]),
                            "mime_type": str(row["mime_type"]),
                            "file_size": int(row["file_size"]),
                        },
                        target_id=None,
                    )
            return len(rows) > 0