from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.core.database import get_pool


async def get_event_evaluations(event_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT e.id, e.event_id, e.server_id, e.punctuality, e.work_quality,
                   e.presentation, e.teamwork, e.client_relation, e.comment, e.created_at,
                   s.first_name, s.last_name, es.role
            FROM evaluations e
            JOIN servers s ON e.server_id = s.id
            JOIN event_staff es ON es.event_id = e.event_id AND es.server_id = e.server_id
            WHERE e.event_id = $1
            ORDER BY e.created_at ASC
            """,
            event_id,
        )
        return [
            {
                "id": str(r["id"]),
                "event_id": str(r["event_id"]),
                "server_id": str(r["server_id"]),
                "server_name": f"{r['first_name']} {r['last_name']}".strip(),
                "role": r["role"],
                "punctuality": r["punctuality"],
                "work_quality": r["work_quality"],
                "presentation": r["presentation"],
                "teamwork": r["teamwork"],
                "client_relation": r["client_relation"],
                "comment": r["comment"],
                "created_at": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else r["created_at"],
            }
            for r in rows
        ]


async def get_evaluation(event_id: str, evaluation_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT e.id, e.event_id, e.server_id, e.punctuality, e.work_quality,
                   e.presentation, e.teamwork, e.client_relation, e.comment, e.created_at,
                   s.first_name, s.last_name, es.role
            FROM evaluations e
            JOIN servers s ON e.server_id = s.id
            JOIN event_staff es ON es.event_id = e.event_id AND es.server_id = e.server_id
            WHERE e.event_id = $1 AND e.id = $2
            LIMIT 1
            """,
            event_id,
            evaluation_id,
        )
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "event_id": str(row["event_id"]),
            "server_id": str(row["server_id"]),
            "server_name": f"{row['first_name']} {row['last_name']}".strip(),
            "role": row["role"],
            "punctuality": row["punctuality"],
            "work_quality": row["work_quality"],
            "presentation": row["presentation"],
            "teamwork": row["teamwork"],
            "client_relation": row["client_relation"],
            "comment": row["comment"],
            "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else row["created_at"],
        }


async def create_evaluation(event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT id, status FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] != "COMPLETED":
                raise HTTPException(
                    status_code=400,
                    detail="Les évaluations ne peuvent être créées que pour des événements terminés.",
                )

            server_id = payload.get("server_id")
            if not server_id:
                raise HTTPException(status_code=400, detail="server_id est requis.")

            staff_row = await conn.fetchrow(
                """
                SELECT id FROM event_staff
                WHERE event_id = $1 AND server_id = $2 AND assignment_status = 'CONFIRMED'
                LIMIT 1
                """,
                event_id,
                server_id,
            )
            if not staff_row:
                raise HTTPException(
                    status_code=400,
                    detail="Ce serveur n'est pas confirmé pour cet événement.",
                )

            existing = await conn.fetchrow(
                "SELECT id FROM evaluations WHERE event_id = $1 AND server_id = $2",
                event_id,
                server_id,
            )
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="Une évaluation existe déjà pour ce serveur sur cet événement.",
                )

            row = await conn.fetchrow(
                """
                INSERT INTO evaluations (event_id, server_id, punctuality, work_quality,
                                        presentation, teamwork, client_relation, comment)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, event_id, server_id, punctuality, work_quality,
                          presentation, teamwork, client_relation, comment, created_at
                """,
                event_id,
                server_id,
                payload["punctuality"],
                payload["work_quality"],
                payload["presentation"],
                payload["teamwork"],
                payload["client_relation"],
                payload.get("comment"),
            )

            server_name_row = await conn.fetchrow(
                "SELECT first_name, last_name FROM servers WHERE id = $1",
                server_id,
            )
            role_row = await conn.fetchrow(
                "SELECT role FROM event_staff WHERE event_id = $1 AND server_id = $2",
                event_id,
                server_id,
            )
            server_name = (
                f"{server_name_row['first_name']} {server_name_row['last_name']}".strip()
                if server_name_row
                else "Inconnu"
            )
            role = role_row["role"] if role_row else "Staff"

            return {
                "id": str(row["id"]),
                "event_id": str(row["event_id"]),
                "server_id": str(row["server_id"]),
                "server_name": server_name,
                "role": role,
                "punctuality": row["punctuality"],
                "work_quality": row["work_quality"],
                "presentation": row["presentation"],
                "teamwork": row["teamwork"],
                "client_relation": row["client_relation"],
                "comment": row["comment"],
                "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else row["created_at"],
            }


async def update_evaluation(event_id: str, evaluation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT id, status FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] != "COMPLETED":
                raise HTTPException(
                    status_code=400,
                    detail="Les évaluations ne peuvent être modifiées que pour des événements terminés.",
                )

            eval_row = await conn.fetchrow(
                "SELECT id, server_id FROM evaluations WHERE id = $1 AND event_id = $2",
                evaluation_id,
                event_id,
            )
            if not eval_row:
                raise HTTPException(status_code=404, detail="Évaluation introuvable.")

            set_parts = []
            values = [evaluation_id, event_id]
            idx = 3

            for field in ("punctuality", "work_quality", "presentation", "teamwork", "client_relation"):
                if field in payload and payload[field] is not None:
                    set_parts.append(f"{field} = ${idx}")
                    values.append(payload[field])
                    idx += 1

            if "comment" in payload:
                set_parts.append(f"comment = ${idx}")
                values.append(payload["comment"])
                idx += 1

            if not set_parts:
                raise HTTPException(status_code=400, detail="Aucune modification fournie.")

            query = f"""
                UPDATE evaluations
                SET {', '.join(set_parts)}
                WHERE id = $1 AND event_id = $2
                RETURNING id, event_id, server_id, punctuality, work_quality,
                          presentation, teamwork, client_relation, comment, created_at
            """
            row = await conn.fetchrow(query, *values)

            server_name_row = await conn.fetchrow(
                "SELECT first_name, last_name FROM servers WHERE id = $1",
                row["server_id"],
            )
            role_row = await conn.fetchrow(
                "SELECT role FROM event_staff WHERE event_id = $1 AND server_id = $2",
                event_id,
                row["server_id"],
            )
            server_name = (
                f"{server_name_row['first_name']} {server_name_row['last_name']}".strip()
                if server_name_row
                else "Inconnu"
            )
            role = role_row["role"] if role_row else "Staff"

            return {
                "id": str(row["id"]),
                "event_id": str(row["event_id"]),
                "server_id": str(row["server_id"]),
                "server_name": server_name,
                "role": role,
                "punctuality": row["punctuality"],
                "work_quality": row["work_quality"],
                "presentation": row["presentation"],
                "teamwork": row["teamwork"],
                "client_relation": row["client_relation"],
                "comment": row["comment"],
                "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else row["created_at"],
            }


async def delete_evaluation(event_id: str, evaluation_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT id, status FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] != "COMPLETED":
                raise HTTPException(
                    status_code=400,
                    detail="Les évaluations ne peuvent être supprimées que pour des événements terminés.",
                )

            eval_row = await conn.fetchrow(
                "SELECT id FROM evaluations WHERE id = $1 AND event_id = $2",
                evaluation_id,
                event_id,
            )
            if not eval_row:
                raise HTTPException(status_code=404, detail="Évaluation introuvable.")

            await conn.execute(
                "DELETE FROM evaluations WHERE id = $1 AND event_id = $2",
                evaluation_id,
                event_id,
            )
            return {"deleted": True}
