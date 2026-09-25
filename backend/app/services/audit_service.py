import json
from datetime import datetime
from typing import Any

import asyncpg

from app.core.database import get_pool


async def log_audit_action(
    conn: asyncpg.Connection,
    actor_id: str,
    action: str,
    detail: dict,
    target_id: str | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO audit_log (actor_user_id, target_user_id, action, detail)
        VALUES ($1, $2, $3, $4::jsonb)
        """,
        str(actor_id),
        str(target_id) if target_id else None,
        action,
        json.dumps(detail),
    )


def _format_dt(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


async def list_audit_logs(
    action: str | None = None,
    actor_user_id: str | None = None,
    target_user_id: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        where_clauses: list[str] = []
        params: list[Any] = []
        idx = 1

        if action:
            where_clauses.append(f"al.action = ${idx}")
            params.append(action)
            idx += 1

        if actor_user_id:
            where_clauses.append(f"al.actor_user_id = ${idx}::UUID")
            params.append(actor_user_id)
            idx += 1

        if target_user_id:
            where_clauses.append(f"al.target_user_id = ${idx}::UUID")
            params.append(target_user_id)
            idx += 1

        if created_after:
            where_clauses.append(f"al.created_at >= ${idx}")
            params.append(created_after)
            idx += 1

        if created_before:
            where_clauses.append(f"al.created_at <= ${idx}")
            params.append(created_before)
            idx += 1

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        try:
            total_row = await conn.fetchrow(
                f"SELECT COUNT(*) AS total FROM audit_log al {where_sql}",
                *params,
            )
        except asyncpg.InvalidTextRepresentationError:
            return [], 0
        total = total_row["total"] if total_row else 0

        offset = (page - 1) * page_size
        rows = await conn.fetch(
            f"""
            SELECT
                al.id,
                al.actor_user_id,
                al.target_user_id,
                al.action,
                al.detail,
                al.created_at,
                actor_user.email AS actor_email,
                target_user.email AS target_email
            FROM audit_log al
            LEFT JOIN users AS actor_user ON al.actor_user_id = actor_user.id
            LEFT JOIN users AS target_user ON al.target_user_id = target_user.id
            {where_sql}
            ORDER BY al.created_at DESC, al.id DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
            page_size,
            offset,
        )

        items = []
        for r in rows:
            detail = r["detail"]
            if isinstance(detail, str):
                try:
                    detail = json.loads(detail)
                except (json.JSONDecodeError, TypeError):
                    detail = {}
            items.append({
                "id": str(r["id"]),
                "actor_user_id": str(r["actor_user_id"]) if r["actor_user_id"] else None,
                "target_user_id": str(r["target_user_id"]) if r["target_user_id"] else None,
                "action": r["action"],
                "detail": detail,
                "created_at": _format_dt(r["created_at"]),
                "actor_email": r["actor_email"],
                "target_email": r["target_email"],
            })

        return items, total