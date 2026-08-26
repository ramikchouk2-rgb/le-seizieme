from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.core.database import get_pool


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
            result.append({
                "id": str(r["id"]),
                "server_id": str(r["server_id"]),
                "start_datetime": r["start_datetime"].isoformat() if isinstance(r["start_datetime"], datetime) else str(r["start_datetime"]),
                "end_datetime": r["end_datetime"].isoformat() if isinstance(r["end_datetime"], datetime) else str(r["end_datetime"]),
                "status": r["status"],
                "note": r["note"],
                "conflict": False,
                "conflict_reason": None,
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

            start_dt = data["start_datetime"]
            end_dt = data["end_datetime"]
            if isinstance(start_dt, str):
                start_dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            if isinstance(end_dt, str):
                end_dt = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))

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

            start_dt = data.get("start_datetime", avail_row["start_datetime"])
            end_dt = data.get("end_datetime", avail_row["end_datetime"])
            if isinstance(start_dt, str):
                start_dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            if isinstance(end_dt, str):
                end_dt = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))

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

            event_conflict = await conn.fetch(
                """
                SELECT e.id, e.name, e.start_datetime, e.end_datetime
                FROM events e
                JOIN event_staff es ON e.id = es.event_id
                WHERE es.server_id = $1
                  AND e.status IN ('CONFIRMED', 'IN_PROGRESS')
                  AND tsrange(e.start_datetime::timestamp, e.end_datetime::timestamp) && tsrange($2::timestamp, $3::timestamp)
                  AND NOT EXISTS (
                      SELECT 1 FROM server_availability sa
                      WHERE sa.server_id = $1
                        AND sa.id = $4
                        AND tsrange(sa.start_datetime::timestamp, sa.end_datetime::timestamp) && tsrange(e.start_datetime::timestamp, e.end_datetime::timestamp)
                  )
                LIMIT 1
                """,
                server_id,
                start_dt,
                end_dt,
                availability_id,
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
                  AND e.start_datetime < $3
                  AND e.end_datetime > $2
                """,
                server_id,
                avail_row["start_datetime"],
                avail_row["end_datetime"],
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
            event_row["start_datetime"],
            event_row["end_datetime"],
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
