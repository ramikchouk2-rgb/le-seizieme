from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.core.database import get_pool
from app.utils.datetime_utils import to_naive_utc


def _naive_utc(value: datetime) -> datetime:
    normalized = to_naive_utc(value)
    if normalized is None:
        raise ValueError("Date et heure invalide.")
    return normalized


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _naive_utc(value)
    if isinstance(value, str):
        try:
            return _naive_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except (ValueError, TypeError):
            raise ValueError("Date et heure invalide.")
    raise ValueError("Date et heure invalide.")


def _coerce_datetime_http(value: Any) -> datetime:
    try:
        return _coerce_datetime(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def get_event_scheduling_conflict(
    conn,
    server_id: str,
    event_start: datetime,
    event_end: datetime,
    exclude_event_id: str | None = None,
) -> dict[str, Any]:
    event_start = _naive_utc(event_start)
    event_end = _naive_utc(event_end)
    availability_row = await conn.fetchrow(
        """
        SELECT id
        FROM server_availability
        WHERE server_id = $1
          AND start_datetime <= $2
          AND end_datetime >= $3
          AND status = 'AVAILABLE'
        LIMIT 1
        """,
        server_id,
        event_start,
        event_end,
    )
    if not availability_row:
        return {
            "conflict": True,
            "conflict_reason": "Aucune disponibilité disponible ne couvre cet événement.",
        }

    rows = await conn.fetch(
        """
        SELECT e.id, e.name, e.start_datetime, e.end_datetime
        FROM event_staff es
        JOIN events e ON e.id = es.event_id
        WHERE es.server_id = $1
          AND e.status IN ('CONFIRMED', 'IN_PROGRESS')
          AND e.start_datetime < $3
          AND e.end_datetime > $2
          AND ($4::uuid IS NULL OR e.id <> $4::uuid)
        ORDER BY e.start_datetime ASC
        LIMIT 1
        """,
        server_id,
        event_start,
        event_end,
        exclude_event_id,
    )
    if not rows:
        return {"conflict": False, "conflict_reason": None}

    event = rows[0]
    return {
        "conflict": True,
        "conflict_reason": (
            f"Conflit avec l'événement « {event['name']} » "
            f"({event['start_datetime'].strftime('%d/%m/%Y %H:%M')})."
        ),
    }


async def get_availability_scheduling_conflict(
    conn,
    server_id: str,
    start_datetime: datetime,
    end_datetime: datetime,
) -> dict[str, Any]:
    start_datetime = _naive_utc(start_datetime)
    end_datetime = _naive_utc(end_datetime)
    rows = await conn.fetch(
        """
        SELECT e.id, e.name, e.start_datetime, e.end_datetime
        FROM events e
        JOIN event_staff es ON e.id = es.event_id
        WHERE es.server_id = $1
          AND e.status IN ('CONFIRMED', 'IN_PROGRESS')
          AND e.start_datetime < $3
          AND e.end_datetime > $2
        ORDER BY e.start_datetime ASC
        LIMIT 1
        """,
        server_id,
        start_datetime,
        end_datetime,
    )
    if not rows:
        return {"conflict": False, "conflict_reason": None}

    event = rows[0]
    return {
        "conflict": True,
        "conflict_reason": (
            f"Conflit avec l'événement « {event['name']} » "
            f"({event['start_datetime'].strftime('%d/%m/%Y %H:%M')})."
        ),
    }


async def get_server_availability(server_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        server_row = await conn.fetchrow(
            "SELECT id FROM servers WHERE id = $1",
            server_id,
        )
        if not server_row:
            raise HTTPException(status_code=404, detail="Serveur introuvable.")

        rows = await conn.fetch(
            """
            SELECT id, server_id, start_datetime, end_datetime, status, note
            FROM server_availability
            WHERE server_id = $1
            ORDER BY start_datetime ASC
            """,
            server_id,
        )
        result = []
        for r in rows:
            conflict = await get_availability_scheduling_conflict(
                conn,
                server_id,
                r["start_datetime"],
                r["end_datetime"],
            )
            result.append({
                "id": str(r["id"]),
                "server_id": str(r["server_id"]),
                "start_datetime": r["start_datetime"].isoformat() if isinstance(r["start_datetime"], datetime) else str(r["start_datetime"]),
                "end_datetime": r["end_datetime"].isoformat() if isinstance(r["end_datetime"], datetime) else str(r["end_datetime"]),
                "status": r["status"],
                "note": r["note"],
                **conflict,
            })
        return result


async def create_availability(server_id: str, data: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            server_row = await conn.fetchrow(
                "SELECT id, is_active FROM servers WHERE id = $1",
                server_id,
            )
            if not server_row:
                raise HTTPException(status_code=404, detail="Serveur introuvable.")
            if not server_row["is_active"]:
                raise HTTPException(status_code=400, detail="Serveur inactif.")

            start_dt = _coerce_datetime_http(data["start_datetime"])
            end_dt = _coerce_datetime_http(data["end_datetime"])

            if start_dt >= end_dt:
                raise HTTPException(status_code=400, detail="start_datetime doit être inférieur à end_datetime.")

            overlap = await conn.fetch(
                """
                SELECT id
                FROM server_availability
                WHERE server_id = $1
                  AND tsrange(start_datetime::timestamp, end_datetime::timestamp) && tsrange($2::timestamp, $3::timestamp)
                LIMIT 1
                """,
                server_id,
                start_dt,
                end_dt,
            )
            if overlap:
                raise HTTPException(
                    status_code=400,
                    detail="Cette période chevauche une disponibilité existante.",
                )

            event_conflict = await conn.fetch(
                """
                SELECT e.id, e.name, e.start_datetime, e.end_datetime
                FROM events e
                JOIN event_staff es ON e.id = es.event_id
                WHERE es.server_id = $1
                  AND e.status IN ('CONFIRMED', 'IN_PROGRESS')
                  AND tsrange(e.start_datetime::timestamp, e.end_datetime::timestamp) && tsrange($2::timestamp, $3::timestamp)
                LIMIT 1
                """,
                server_id,
                start_dt,
                end_dt,
            )
            if event_conflict:
                raise HTTPException(
                    status_code=400,
                    detail="Cette période entre en conflit avec un événement confirmé ou en cours.",
                )

            row = await conn.fetchrow(
                """
                INSERT INTO server_availability (server_id, start_datetime, end_datetime, status, note)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, server_id, start_datetime, end_datetime, status, note
                """,
                server_id,
                start_dt,
                end_dt,
                data.get("status", "AVAILABLE"),
                data.get("note"),
            )
            return {
                "id": str(row["id"]),
                "server_id": str(row["server_id"]),
                "start_datetime": row["start_datetime"].isoformat() if isinstance(row["start_datetime"], datetime) else str(row["start_datetime"]),
                "end_datetime": row["end_datetime"].isoformat() if isinstance(row["end_datetime"], datetime) else str(row["end_datetime"]),
                "status": row["status"],
                "note": row["note"],
                "conflict": False,
                "conflict_reason": None,
            }


async def update_availability(server_id: str, availability_id: str, data: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            server_row = await conn.fetchrow(
                "SELECT id, is_active FROM servers WHERE id = $1",
                server_id,
            )
            if not server_row:
                raise HTTPException(status_code=404, detail="Serveur introuvable.")
            if not server_row["is_active"]:
                raise HTTPException(status_code=400, detail="Serveur inactif.")

            avail_row = await conn.fetchrow(
                "SELECT id, server_id, start_datetime, end_datetime FROM server_availability WHERE id = $1 AND server_id = $2",
                availability_id,
                server_id,
            )
            if not avail_row:
                raise HTTPException(status_code=404, detail="Disponibilité introuvable.")

            start_dt = _coerce_datetime_http(data.get("start_datetime", avail_row["start_datetime"]))
            end_dt = _coerce_datetime_http(data.get("end_datetime", avail_row["end_datetime"]))

            if start_dt >= end_dt:
                raise HTTPException(status_code=400, detail="start_datetime doit être inférieur à end_datetime.")

            overlap = await conn.fetch(
                """
                SELECT id
                FROM server_availability
                WHERE server_id = $1
                  AND id <> $2
                  AND tsrange(start_datetime::timestamp, end_datetime::timestamp) && tsrange($3::timestamp, $4::timestamp)
                LIMIT 1
                """,
                server_id,
                availability_id,
                start_dt,
                end_dt,
            )
            if overlap:
                raise HTTPException(
                    status_code=400,
                    detail="Cette période chevauche une disponibilité existante.",
                )

            current_start = _naive_utc(avail_row["start_datetime"])
            current_end = _naive_utc(avail_row["end_datetime"])
            interval_changed = start_dt != current_start or end_dt != current_end

            event_conflict = None
            if interval_changed:
                event_conflict = await conn.fetch(
                    """
                    SELECT e.id, e.name, e.start_datetime, e.end_datetime
                    FROM events e
                    JOIN event_staff es ON e.id = es.event_id
                    WHERE es.server_id = $1
                      AND e.status IN ('CONFIRMED', 'IN_PROGRESS')
                      AND tsrange(e.start_datetime::timestamp, e.end_datetime::timestamp) && tsrange($2::timestamp, $3::timestamp)
                    LIMIT 1
                    """,
                    server_id,
                    start_dt,
                    end_dt,
                )
            if event_conflict:
                raise HTTPException(
                    status_code=400,
                    detail="Cette période entre en conflit avec un événement confirmé ou en cours.",
                )

            set_clauses = []
            params = []
            idx = 1
            if "start_datetime" in data:
                set_clauses.append(f"start_datetime = ${idx}")
                params.append(start_dt)
                idx += 1
            if "end_datetime" in data:
                set_clauses.append(f"end_datetime = ${idx}")
                params.append(end_dt)
                idx += 1
            if "status" in data:
                set_clauses.append(f"status = ${idx}")
                params.append(data["status"])
                idx += 1
            if "note" in data:
                set_clauses.append(f"note = ${idx}")
                params.append(data["note"])
                idx += 1

            if not set_clauses:
                row = await conn.fetchrow(
                    "SELECT id, server_id, start_datetime, end_datetime, status, note FROM server_availability WHERE id = $1",
                    availability_id,
                )
                return {
                    "id": str(row["id"]),
                    "server_id": str(row["server_id"]),
                    "start_datetime": row["start_datetime"].isoformat() if isinstance(row["start_datetime"], datetime) else str(row["start_datetime"]),
                    "end_datetime": row["end_datetime"].isoformat() if isinstance(row["end_datetime"], datetime) else str(row["end_datetime"]),
                    "status": row["status"],
                    "note": row["note"],
                    "conflict": False,
                    "conflict_reason": None,
                }

            params.append(availability_id)
            sql = f"""
                UPDATE server_availability
                SET {', '.join(set_clauses)}
                WHERE id = ${idx}
                RETURNING id, server_id, start_datetime, end_datetime, status, note
            """
            row = await conn.fetchrow(sql, *params)
            return {
                "id": str(row["id"]),
                "server_id": str(row["server_id"]),
                "start_datetime": row["start_datetime"].isoformat() if isinstance(row["start_datetime"], datetime) else str(row["start_datetime"]),
                "end_datetime": row["end_datetime"].isoformat() if isinstance(row["end_datetime"], datetime) else str(row["end_datetime"]),
                "status": row["status"],
                "note": row["note"],
                "conflict": False,
                "conflict_reason": None,
            }


async def delete_availability(server_id: str, availability_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            server_row = await conn.fetchrow(
                "SELECT id, is_active FROM servers WHERE id = $1",
                server_id,
            )
            if not server_row:
                raise HTTPException(status_code=404, detail="Serveur introuvable.")

            avail_row = await conn.fetchrow(
                "SELECT id, start_datetime, end_datetime FROM server_availability WHERE id = $1 AND server_id = $2",
                availability_id,
                server_id,
            )
            if not avail_row:
                raise HTTPException(status_code=404, detail="Disponibilité introuvable.")

            conflict_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM events e
                JOIN event_staff es ON e.id = es.event_id
                WHERE es.server_id = $1
                  AND e.status IN ('CONFIRMED', 'IN_PROGRESS')
                  AND tsrange(e.start_datetime::timestamp, e.end_datetime::timestamp) && tsrange($2::timestamp, $3::timestamp)
                """,
                server_id,
                _naive_utc(avail_row["start_datetime"]),
                _naive_utc(avail_row["end_datetime"]),
            )

            if conflict_count > 0:
                raise HTTPException(
                    status_code=409,
                    detail="Impossible de supprimer cette disponibilité : elle est utilisée par un événement confirmé ou en cours.",
                )

            await conn.execute(
                "DELETE FROM server_availability WHERE id = $1",
                availability_id,
            )
            return {"deleted": True}


async def check_availability_for_event(server_id: str, event_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        server_row = await conn.fetchrow(
            "SELECT id, is_active FROM servers WHERE id = $1",
            server_id,
        )
        if not server_row:
            raise HTTPException(status_code=404, detail="Serveur introuvable.")
        if not server_row["is_active"]:
            return {
                "server_id": server_id,
                "event_id": event_id,
                "available": False,
                "reason": "SERVER_INACTIVE",
            }

        event_row = await conn.fetchrow(
            "SELECT id, start_datetime, end_datetime, status FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")
        if event_row["status"] in ("CANCELLED", "COMPLETED"):
            return {
                "server_id": server_id,
                "event_id": event_id,
                "available": True,
                "reason": None,
            }

        event_start = _naive_utc(event_row["start_datetime"])
        event_end = _naive_utc(event_row["end_datetime"])
        avail_row = await conn.fetchrow(
            """
            SELECT id, status
            FROM server_availability
            WHERE server_id = $1
              AND start_datetime <= $2
              AND end_datetime >= $3
            LIMIT 1
            """,
            server_id,
            event_start,
            event_end,
        )
        if not avail_row:
            return {
                "server_id": server_id,
                "event_id": event_id,
                "available": False,
                "reason": "OUTSIDE_AVAILABILITY",
            }
        if avail_row["status"] != "AVAILABLE":
            return {
                "server_id": server_id,
                "event_id": event_id,
                "available": False,
                "reason": "UNAVAILABLE",
            }

        assigned_row = await conn.fetchrow(
            """
            SELECT es.id
            FROM event_staff es
            WHERE es.server_id = $1
              AND es.event_id = $2
              AND es.assignment_status IN ('CONFIRMED', 'PROPOSED')
            LIMIT 1
            """,
            server_id,
            event_id,
        )
        if assigned_row:
            return {
                "server_id": server_id,
                "event_id": event_id,
                "available": False,
                "reason": "ALREADY_ASSIGNED",
            }

        return {
            "server_id": server_id,
            "event_id": event_id,
            "available": True,
            "reason": None,
        }
