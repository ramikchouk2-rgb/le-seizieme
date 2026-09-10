from datetime import datetime, timezone


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """
    Convert a datetime to timezone-naive UTC.

    Args:
        dt: A datetime object (timezone-aware or naive)

    Returns:
        A timezone-naive datetime representing the same instant in UTC,
        or None if input is None.
    """
    if dt is None:
        return None

    if dt.tzinfo is not None:
        # Convert to UTC then strip timezone info
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    return dt


def now_naive_utc() -> datetime:
    """
    Get current UTC time as timezone-naive datetime.

    Returns:
        Current UTC time with no timezone info.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)