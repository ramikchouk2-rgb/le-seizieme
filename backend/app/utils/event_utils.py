from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.database import get_pool
from app.utils.selection_utils import serialize_row


def resolve_event_location(event: dict[str, Any] | None) -> tuple[float, float, bool]:
    """Resolve the venue position of an event.

    Returns ``(latitude, longitude, has_exact_location)``.

    The only accepted source of truth is the event's own ``latitude`` /
    ``longitude`` columns. A server's personal GPS position is never used to
    represent a venue. When the event has no stored coordinates the technical
    fallback (``DEFAULT_EVENT_LATITUDE`` / ``DEFAULT_EVENT_LONGITUDE``) is
    returned together with ``has_exact_location=False`` so callers can mark the
    result as approximate instead of presenting it as the real venue.
    """
    if not event:
        return settings.DEFAULT_EVENT_LATITUDE, settings.DEFAULT_EVENT_LONGITUDE, False

    raw_lat = event.get("latitude")
    raw_lon = event.get("longitude")
    if raw_lat is not None and raw_lon is not None:
        return float(raw_lat), float(raw_lon), True

    return settings.DEFAULT_EVENT_LATITUDE, settings.DEFAULT_EVENT_LONGITUDE, False


async def load_event(event_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT e.id, e.name, e.client_name, e.city_id, c.name AS city_name,
                   e.address, e.latitude, e.longitude,
                   e.start_datetime, e.end_datetime, e.guest_count,
                   e.event_type, e.alcohol_service, e.food_products_count,
                   e.priority, e.is_urgent, e.status, e.notes
            FROM events e
            JOIN cities c ON e.city_id = c.id
            WHERE e.id = $1
            LIMIT 1
            """,
            event_id,
        )
        if not row:
            return None
        event = serialize_row(dict(row))
        _, _, has_exact_location = resolve_event_location(event)
        event["has_exact_location"] = has_exact_location
        return event
