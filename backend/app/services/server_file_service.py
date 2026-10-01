"""Step 24C-D-5: reusable server file storage service.

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

# Image types accepted for a profile photo. Kept as an explicit allowlist; a
# new type is a deliberate code change, never a configuration side effect.
ALLOWED_PROFILE_PHOTO_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

# Leading magic-byte signatures per supported type.
_MAGIC_SIGNATURES: tuple[tuple[str, bytes], ...] = (
    ("image/jpeg", b"\xff\xd8\xff"),
    ("image/png", b"\x89PNG\r\n\x1a\n"),
    # WEBP is a RIFF container: "RIFF" ....size.... "WEBP"
    ("image/webp", b"RIFF"),
)

_MAX_FILENAME_LENGTH = 255
_FILENAME_STRIP_RE = re.compile(r"[^A-Za-z0-9._-]+")
# Path separators and traversal markers are removed outright.
_FILENAME_UNSAFE_RE = re.compile(r"[\\/\x00]")

PROFILE_PHOTO_FILE_TYPE = "PROFILE_PHOTO"


def max_profile_photo_bytes() -> int:
    """Maximum accepted profile photo size in bytes."""
    return settings.MAX_PROFILE_PHOTO_BYTES


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


def sniff_image_mime_type(data: bytes) -> str | None:
    """Return the MIME type implied by the leading bytes, or None."""
    for mime_type, signature in _MAGIC_SIGNATURES:
        if not data.startswith(signature):
            continue
        if mime_type == "image/webp":
            # A bare "RIFF" prefix is not enough to claim WEBP.
            if len(data) >= 12 and data[8:12] == b"WEBP":
                return mime_type
            continue
        return mime_type
    return None


def validate_profile_photo(data: bytes, declared_mime_type: str | None) -> str:
    """Validate photo bytes and return the MIME type to persist.

    Raises HTTPException 400 on any validation failure. The declared MIME type
    is used only as a cross-check: it can reject a file but can never vouch for
    one.
    """
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )

    size = len(data)
    limit = max_profile_photo_bytes()
    if size > limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le fichier est trop volumineux "
                f"({size} octets, maximum {limit} octets)."
            ),
        )

    sniffed = sniff_image_mime_type(data)
    if sniffed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Format d'image non reconnu. Formats acceptés : JPEG, PNG, WebP."
            ),
        )

    if sniffed not in ALLOWED_PROFILE_PHOTO_MIME_TYPES:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'image non autorisé.",
        )

    if declared_mime_type:
        normalized = declared_mime_type.split(";")[0].strip().lower()
        if normalized and normalized != "application/octet-stream" and normalized != sniffed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Le type déclaré ne correspond pas au contenu du fichier."
                ),
            )

    return sniffed


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


async def server_exists(server_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return bool(
            await conn.fetchval("SELECT EXISTS (SELECT 1 FROM servers WHERE id = $1)", server_id)
        )


async def get_current_profile_photo_metadata(server_id: str) -> dict[str, Any] | None:
    """Metadata only. This is what detail responses use; no BYTEA is selected."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, server_id, file_type, mime_type, original_filename,
                   file_size, is_current, created_at
            FROM server_files
            WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
            LIMIT 1
            """,
            server_id,
            PROFILE_PHOTO_FILE_TYPE,
        )
        return _metadata_from_row(dict(row)) if row else None


async def has_profile_photo(server_id: str) -> bool:
    metadata = await get_current_profile_photo_metadata(server_id)
    return metadata is not None


async def load_servers_with_profile_photo(server_ids: list[str]) -> dict[str, bool]:
    """Batched boolean projection. Avoids an N+1 lookup on list endpoints."""
    if not server_ids:
        return {}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
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


async def get_current_profile_photo_content(server_id: str) -> dict[str, Any] | None:
    """Bytes + MIME for the authorized photo endpoint only."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, server_id, file_type, mime_type, original_filename,
                   file_size, is_current, created_at, content
            FROM server_files
            WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
            LIMIT 1
            """,
            server_id,
            PROFILE_PHOTO_FILE_TYPE,
        )
        return dict(row) if row else None


async def upload_profile_photo(
    server_id: str,
    data: bytes,
    declared_mime_type: str | None,
    original_filename: str | None,
) -> dict[str, Any]:
    """Upload or replace the current profile photo.

    Replacement deactivates the previous current file instead of deleting it, so
    history is preserved. The insert and the deactivation happen in one
    transaction with the old row locked, and a partial UNIQUE index on
    (server_id, file_type) WHERE is_current guarantees at most one current file
    even under concurrent uploads.
    """
    mime_type = validate_profile_photo(data, declared_mime_type)
    safe_filename = sanitize_filename(original_filename)
    file_size = len(data)

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM servers WHERE id = $1)", server_id
            )
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Serveur introuvable.",
                )

            await conn.execute(
                """
                UPDATE server_files
                SET is_current = FALSE, updated_at = NOW()
                WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
                """,
                server_id,
                PROFILE_PHOTO_FILE_TYPE,
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
                PROFILE_PHOTO_FILE_TYPE,
                data,
                mime_type,
                safe_filename,
                file_size,
            )

    return _metadata_from_row(dict(row))


async def delete_current_profile_photo(server_id: str) -> bool:
    """Deactivate the current profile photo.

    Returns True when a photo was removed. The row is retained as history
    (`is_current = FALSE`) rather than hard-deleted, so the operation is
    reversible and audit-friendly.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE server_files
            SET is_current = FALSE, updated_at = NOW()
            WHERE server_id = $1 AND file_type = $2 AND is_current = TRUE
            RETURNING id
            """,
            server_id,
            PROFILE_PHOTO_FILE_TYPE,
        )
    return len(rows) > 0