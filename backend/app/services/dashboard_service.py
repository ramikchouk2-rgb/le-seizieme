from datetime import datetime
from typing import Any

from app.core.database import get_pool


async def load_recent_activity(limit: int = 10) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        activities: list[dict[str, Any]] = []

        event_rows = await conn.fetch(
            """
            SELECT id, name AS message, created_at, id AS event_id
            FROM events
            WHERE created_at IS NOT NULL
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
        for r in event_rows:
            activities.append({
                "id": f"event-{r['id']}",
                "type": "event_created",
                "message": f"Événement créé : {r['message']}",
                "timestamp": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else str(r["created_at"]),
                "event_id": str(r["event_id"]),
            })

        staff_rows = await conn.fetch(
            """
            SELECT es.id, es.assigned_at, s.first_name, s.last_name, e.name AS event_name, e.id AS event_id
            FROM event_staff es
            JOIN servers s ON es.server_id = s.id
            JOIN events e ON es.event_id = e.id
            WHERE es.assigned_at IS NOT NULL
            ORDER BY es.assigned_at DESC
            LIMIT $1
            """,
            limit,
        )
        for r in staff_rows:
            activities.append({
                "id": f"staff-{r['id']}",
                "type": "staff_assigned",
                "message": f"{r['first_name']} {r['last_name']} assigné à {r['event_name']}",
                "timestamp": r["assigned_at"].isoformat() if isinstance(r["assigned_at"], datetime) else str(r["assigned_at"]),
                "event_id": str(r["event_id"]),
            })

        point_rows = await conn.fetch(
            """
            SELECT id, points, reason, created_at, server_id, event_id
            FROM point_transactions
            WHERE created_at IS NOT NULL
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
        for r in point_rows:
            activities.append({
                "id": f"points-{r['id']}",
                "type": "points_awarded",
                "message": r["reason"] or f"Points attribués : {r['points']} pts",
                "timestamp": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else str(r["created_at"]),
                "event_id": str(r["event_id"]) if r["event_id"] else None,
            })

        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
