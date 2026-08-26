from datetime import datetime
from typing import Any

from app.core.database import get_pool
from app.utils.selection_utils import serialize_row


async def load_event(event_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT e.id, e.name, e.client_name, e.city_id, c.name AS city_name,
                   e.address, e.start_datetime, e.end_datetime, e.guest_count,
                   e.event_type, e.alcohol_service, e.food_products_count,
                   e.priority, e.is_urgent, e.status, e.notes,
                   sl.latitude AS event_latitude,
                   sl.longitude AS event_longitude
            FROM events e
            JOIN cities c ON e.city_id = c.id
            LEFT JOIN server_locations sl ON sl.city_id = e.city_id AND sl.is_current = TRUE
            WHERE e.id = $1
            LIMIT 1
            """,
            event_id,
        )
        if not row:
            return None
        return serialize_row(dict(row))
