import json

import asyncpg


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