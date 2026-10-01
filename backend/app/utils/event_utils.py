from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.config import settings
from app.core.database import get_pool
from app.utils.selection_utils import serialize_row


class LocationSource(str, Enum):
    """Where a resolved venue position came from.

    Internal diagnostic detail. It is deliberately NOT exposed on the public
    API: clients receive the boolean ``has_exact_location``, which carries the
    only meaning they act on.
    """

    EXACT_EVENT = "EXACT_EVENT"
    CITY_REFERENCE = "CITY_REFERENCE"
    GLOBAL_FALLBACK = "GLOBAL_FALLBACK"


@dataclass(frozen=True)
class EventLocation:
    latitude: float
    longitude: float
    has_exact_location: bool
    source: LocationSource


def resolve_event_location_detail(event: dict[str, Any] | None) -> EventLocation:
    """Resolve the venue position of an event.

    Resolution hierarchy, in order:

    1. ``EXACT_EVENT``   - the event stores both ``latitude`` and ``longitude``.
                           ``has_exact_location=True``.
    2. ``CITY_REFERENCE`` - the event has no coordinates but its city does.
                           ``has_exact_location=False``.
    3. ``GLOBAL_FALLBACK`` - neither is available, so the configured technical
                           fallback is used as a last resort.
                           ``has_exact_location=False``.

    A server's personal GPS position is NEVER used at any level: a venue is
    never represented by the location of an employee.
    """
    if event:
        raw_lat = event.get("latitude")
        raw_lon = event.get("longitude")
        if raw_lat is not None and raw_lon is not None:
            return EventLocation(
                float(raw_lat), float(raw_lon), True, LocationSource.EXACT_EVENT
            )

        city_lat = event.get("city_latitude")
        city_lon = event.get("city_longitude")
        if city_lat is not None and city_lon is not None:
            return EventLocation(
                float(city_lat), float(city_lon), False, LocationSource.CITY_REFERENCE
            )

    return EventLocation(
        settings.DEFAULT_EVENT_LATITUDE,
        settings.DEFAULT_EVENT_LONGITUDE,
        False,
        LocationSource.GLOBAL_FALLBACK,
    )


def resolve_event_location(event: dict[str, Any] | None) -> tuple[float, float, bool]:
    """Resolve the venue position of an event.

    Returns ``(latitude, longitude, has_exact_location)``.
    """
    location = resolve_event_location_detail(event)
    return location.latitude, location.longitude, location.has_exact_location


async def load_event(event_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT e.id, e.name, e.client_name, e.city_id, c.name AS city_name,
                   e.address, e.latitude, e.longitude,
                   c.latitude AS city_latitude, c.longitude AS city_longitude,
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
        location = resolve_event_location_detail(event)
        event["has_exact_location"] = location.has_exact_location
        return event
