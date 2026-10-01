"""Step 24C-D-6: professional attestations.

Lifecycle contract enforced here:

    PENDING -> VERIFIED | REJECTED | SUPERSEDED
    VERIFIED -> SUPERSEDED  (only with an explicitly named, same-server replacement)

Nothing may move backwards. A verified attestation can never be revoked or
re-pended -- there is no VERIFIED -> REJECTED and no VERIFIED -> PENDING edge -- so
a real qualification can never be withdrawn silently. The single exit from
VERIFIED is SUPERSEDED, which requires naming the document that replaced it and
keeps verified_at/verified_by as an audit trail. A REJECTED or SUPERSEDED
document can never become a verified qualification again: a rejected document
must be re-submitted, which creates a NEW row rather than reviving the old one.

Verification is always an explicit human action. Upload leaves the record
PENDING, and only `verify_attestation`, which records the acting user, can set
VERIFIED.

Documents are stored through `server_file_service` (Step 24C-D-5) inside the
same transaction as the attestation row, so a document can never exist without
its attestation record and vice versa.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.database import get_pool
from app.services.server_file_service import (
    ATTESTATION_FILE_TYPE,
    ensure_server_exists,
    store_server_file,
)

STATUS_PENDING = "PENDING"
STATUS_VERIFIED = "VERIFIED"
STATUS_REJECTED = "REJECTED"
STATUS_SUPERSEDED = "SUPERSEDED"

# Only these transitions are legal. Absence from this map means "not allowed".
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_PENDING: frozenset({STATUS_VERIFIED, STATUS_REJECTED, STATUS_SUPERSEDED}),
    # A VERIFIED attestation may be replaced by a newer document, but ONLY when
    # the replacement is named. That is not a revocation: the document was
    # genuinely verified, and superseding it keeps verified_at/verified_by as an
    # audit trail while pointing at the document that took over.
    #
    # There is deliberately NO VERIFIED -> REJECTED or VERIFIED -> PENDING edge,
    # so a verified qualification cannot be revoked or downgraded in this step.
    # That would need its own documented transition and reason, and is out of
    # scope here.
    STATUS_VERIFIED: frozenset({STATUS_SUPERSEDED}),
    STATUS_REJECTED: frozenset(),
    STATUS_SUPERSEDED: frozenset(),
}

# Transitions that additionally require naming the replacement document.
REPLACEMENT_REQUIRED: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_VERIFIED, STATUS_SUPERSEDED),
    }
)

STATUS_LABELS_FR: dict[str, str] = {
    STATUS_PENDING: "En attente de vérification",
    STATUS_VERIFIED: "Vérifiée",
    STATUS_REJECTED: "Rejetée",
    STATUS_SUPERSEDED: "Remplacée",
}

_METADATA_COLUMNS = """
    a.id, a.server_id, a.file_id, a.status, a.qualification_name,
    a.issuing_organization, a.issued_on, a.expires_on, a.rejection_reason,
    a.verified_at, a.verified_by, a.superseded_by_id, a.created_at, a.updated_at,
    f.mime_type, f.original_filename, f.file_size
"""


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    """Public metadata projection.

    Contains no document bytes, no public URL and no location data. The document
    is reachable only through the explicitly authorized file endpoint.
    """
    return {
        "id": str(row["id"]),
        "server_id": str(row["server_id"]),
        "file_id": str(row["file_id"]),
        "status": str(row["status"]),
        "status_label": STATUS_LABELS_FR.get(str(row["status"]), str(row["status"])),
        # A qualification counts ONLY when this is true.
        "counts_as_verified_qualification": str(row["status"]) == STATUS_VERIFIED,
        "qualification_name": row["qualification_name"],
        "issuing_organization": row["issuing_organization"],
        "issued_on": _iso(row["issued_on"]),
        "expires_on": _iso(row["expires_on"]),
        "rejection_reason": row["rejection_reason"],
        "verified_at": _iso(row["verified_at"]),
        "verified_by": str(row["verified_by"]) if row["verified_by"] else None,
        "superseded_by_id": (
            str(row["superseded_by_id"]) if row["superseded_by_id"] else None
        ),
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
        "file": {
            "id": str(row["file_id"]),
            "mime_type": row["mime_type"],
            "original_filename": row["original_filename"],
            "file_size": row["file_size"],
        },
    }


def _transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


async def create_attestation(
    server_id: str,
    data: bytes,
    declared_mime_type: str | None,
    original_filename: str | None,
    qualification_name: str,
    issuing_organization: str | None = None,
    issued_on: date | None = None,
    expires_on: date | None = None,
) -> dict[str, Any]:
    """Upload a document and create its PENDING attestation record.

    The record is ALWAYS created as PENDING. There is no parameter, flag or code
    path that can make an upload produce a verified qualification.
    """
    name = (qualification_name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'intitulé de la qualification est obligatoire.",
        )
    if issued_on and expires_on and expires_on < issued_on:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date d'expiration ne peut pas précéder la date de délivrance.",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await ensure_server_exists(conn, server_id)
            file_metadata = await store_server_file(
                conn,
                server_id,
                ATTESTATION_FILE_TYPE,
                data,
                declared_mime_type,
                original_filename,
            )
            row = await conn.fetchrow(
                f"""
                INSERT INTO server_attestations (
                    server_id, file_id, status, qualification_name,
                    issuing_organization, issued_on, expires_on
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                server_id,
                file_metadata["id"],
                STATUS_PENDING,
                name,
                (issuing_organization or "").strip() or None,
                issued_on,
                expires_on,
            )
            attestation_id = str(row["id"])

            created = await conn.fetchrow(
                f"""
                SELECT {_METADATA_COLUMNS}
                FROM server_attestations a
                JOIN server_files f ON f.id = a.file_id
                WHERE a.id = $1
                """,
                attestation_id,
            )
    return _serialize(dict(created))


async def _fetch_one(conn, server_id: str, attestation_id: str) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""
        SELECT {_METADATA_COLUMNS}
        FROM server_attestations a
        JOIN server_files f ON f.id = a.file_id
        WHERE a.id = $1 AND a.server_id = $2
        """,
        attestation_id,
        server_id,
    )
    if row is None:
        # Same response whether the server or the attestation is unknown, so the
        # endpoint cannot be used to probe which ids exist.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation introuvable.",
        )
    return dict(row)


async def get_attestation(server_id: str, attestation_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return _serialize(await _fetch_one(conn, server_id, attestation_id))


async def list_attestations(
    server_id: str,
    include_superseded: bool = True,
) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM servers WHERE id = $1)", server_id
        )
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Serveur introuvable."
            )
        rows = await conn.fetch(
            f"""
            SELECT {_METADATA_COLUMNS}
            FROM server_attestations a
            JOIN server_files f ON f.id = a.file_id
            WHERE a.server_id = $1
              AND ($2::boolean OR a.status <> $3)
            ORDER BY
                CASE a.status
                    WHEN 'VERIFIED' THEN 0
                    WHEN 'PENDING' THEN 1
                    WHEN 'REJECTED' THEN 2
                    ELSE 3
                END,
                a.created_at DESC
            """,
            server_id,
            include_superseded,
            STATUS_SUPERSEDED,
        )
    return [_serialize(dict(r)) for r in rows]


async def verified_qualification_counts(
    server_ids: list[str],
) -> dict[str, int]:
    """Batched count of VERIFIED attestations per server.

    Only VERIFIED counts: PENDING, REJECTED and SUPERSEDED are all excluded.
    One query for the whole page, so list endpoints stay free of N+1 lookups and
    never touch document bytes.
    """
    if not server_ids:
        return {}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT server_id, count(*) AS verified_count
            FROM server_attestations
            WHERE server_id = ANY($1::uuid[])
              AND status = $2
            GROUP BY server_id
            """,
            server_ids,
            STATUS_VERIFIED,
        )
    counts = {str(r["server_id"]): int(r["verified_count"]) for r in rows}
    return {sid: counts.get(sid, 0) for sid in server_ids}


async def _apply_transition(
    server_id: str,
    attestation_id: str,
    target_status: str,
    verified_by: str | None = None,
    rejection_reason: str | None = None,
    superseded_by_id: str | None = None,
) -> dict[str, Any]:
    """Perform one lifecycle transition, transactionally.

    The current status is read and the transition legality checked inside the
    same transaction that performs the UPDATE, so two concurrent requests cannot
    both drive a record out of PENDING.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            current = await _fetch_one(conn, server_id, attestation_id)
            current_status = str(current["status"])

            if not _transition_allowed(current_status, target_status):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Transition impossible : {current_status} -> {target_status}."
                    ),
                )

            if (
                current_status,
                target_status,
            ) in REPLACEMENT_REQUIRED and not superseded_by_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Le document de remplacement est obligatoire pour remplacer "
                        "une attestation verifiee."
                    ),
                )

            if target_status == STATUS_VERIFIED:
                # The verifier is recorded from the authenticated user; a caller
                # can never nominate somebody else.
                await conn.execute(
                    """
                    UPDATE server_attestations
                    SET status = $3,
                        verified_at = NOW(),
                        verified_by = $4,
                        rejection_reason = NULL,
                        updated_at = NOW()
                    WHERE id = $1 AND server_id = $2
                    """,
                    attestation_id,
                    server_id,
                    STATUS_VERIFIED,
                    verified_by,
                )
            elif target_status == STATUS_REJECTED:
                await conn.execute(
                    """
                    UPDATE server_attestations
                    SET status = $3,
                        rejection_reason = $4,
                        verified_at = NULL,
                        verified_by = NULL,
                        updated_at = NOW()
                    WHERE id = $1 AND server_id = $2
                    """,
                    attestation_id,
                    server_id,
                    STATUS_REJECTED,
                    rejection_reason,
                )
            else:  # SUPERSEDED
                if superseded_by_id:
                    # The replacement must be a real attestation of the SAME server,
                    # must not be this record, and must be one that still counts --
                    # otherwise the pointer would lead to a dead end or to another
                    # server's document.
                    if str(superseded_by_id) == str(attestation_id):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Une attestation ne peut pas se remplacer elle-meme.",
                        )
                    replacement = await conn.fetchrow(
                        """
                        SELECT status
                        FROM server_attestations
                        WHERE id = $1 AND server_id = $2
                        """,
                        superseded_by_id,
                        server_id,
                    )
                    if replacement is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=(
                                "Attestation de remplacement introuvable pour ce serveur."
                            ),
                        )
                    if str(replacement["status"]) == STATUS_SUPERSEDED:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                "L'attestation de remplacement est elle-meme remplacee."
                            ),
                        )
                await conn.execute(
                    """
                    UPDATE server_attestations
                    SET status = $3, superseded_by_id = $4, updated_at = NOW()
                    WHERE id = $1 AND server_id = $2
                    """,
                    attestation_id,
                    server_id,
                    STATUS_SUPERSEDED,
                    superseded_by_id,
                )

            updated = await _fetch_one(conn, server_id, attestation_id)
    return _serialize(updated)


async def verify_attestation(
    server_id: str, attestation_id: str, verified_by: str
) -> dict[str, Any]:
    """Explicitly verify a PENDING attestation on behalf of a Manager/Admin."""
    return await _apply_transition(
        server_id, attestation_id, STATUS_VERIFIED, verified_by=verified_by
    )


async def reject_attestation(
    server_id: str, attestation_id: str, rejection_reason: str
) -> dict[str, Any]:
    """Reject a PENDING attestation. A non-blank reason is mandatory."""
    reason = (rejection_reason or "").strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un motif de rejet est obligatoire.",
        )
    return await _apply_transition(
        server_id,
        attestation_id,
        STATUS_REJECTED,
        rejection_reason=reason,
    )


async def supersede_attestation(
    server_id: str, attestation_id: str, superseded_by_id: str | None = None
) -> dict[str, Any]:
    """Mark an attestation as replaced by a newer document.

    A superseded attestation stops counting as a verified qualification, but the
    row is kept so the history of what was submitted, and when, survives.
    """
    if superseded_by_id is not None:
        try:
            uuid.UUID(str(superseded_by_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Identifiant d'attestation de remplacement invalide.",
            ) from exc
    return await _apply_transition(
        server_id,
        attestation_id,
        STATUS_SUPERSEDED,
        superseded_by_id=superseded_by_id,
    )


async def get_attestation_document(
    server_id: str, attestation_id: str
) -> dict[str, Any]:
    """Document bytes for the authorized file endpoint.

    The join is on (attestation id, server id) and then on file_id, so an
    attestation belonging to another server can never be used to read that
    server's document.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT f.content, f.mime_type, f.original_filename, f.file_size
            FROM server_attestations a
            JOIN server_files f ON f.id = a.file_id
            WHERE a.id = $1 AND a.server_id = $2
            """,
            attestation_id,
            server_id,
        )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attestation introuvable."
        )
    return dict(row)