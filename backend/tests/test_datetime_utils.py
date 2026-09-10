from datetime import datetime, timezone, timedelta

from app.utils.datetime_utils import to_naive_utc, now_naive_utc


def test_to_naive_utc_utc_aware():
    """Test UTC-aware datetime is converted to naive UTC correctly."""
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
    result = to_naive_utc(dt)
    assert result == datetime(2024, 1, 15, 10, 30, 45)
    assert result.tzinfo is None


def test_to_naive_utc_non_utc_aware():
    """Test non-UTC aware datetime is converted to naive UTC correctly."""
    paris_tz = timezone(timedelta(hours=1))
    dt = datetime(2024, 1, 15, 11, 30, 45, tzinfo=paris_tz)
    result = to_naive_utc(dt)
    assert result == datetime(2024, 1, 15, 10, 30, 45)
    assert result.tzinfo is None


def test_to_naive_utc_naive():
    """Test naive datetime is returned unchanged."""
    dt = datetime(2024, 1, 15, 10, 30, 45)
    result = to_naive_utc(dt)
    assert result == datetime(2024, 1, 15, 10, 30, 45)
    assert result.tzinfo is None


def test_to_naive_utc_none():
    """Test None input returns None."""
    result = to_naive_utc(None)
    assert result is None


def test_now_naive_utc():
    """Test now_naive_utc returns timezone-naive datetime."""
    result = now_naive_utc()
    assert isinstance(result, datetime)
    assert result.tzinfo is None


def test_load_event_list_upcoming_uses_naive_datetime():
    """Test that load_event_list uses naive datetime for UPCOMING filter."""
    from app.services.event_service import load_event_list
    import asyncio

    async def test():
        # This should not raise an error about timezone-aware/naive mismatch
        result, total = await load_event_list(
            search=None,
            city=None,
            status=None,
            priority=None,
            urgent=None,
            staffing=None,
            date_range="UPCOMING",
            sort_by="date",
            sort_order="asc",
            page=1,
            page_size=5,
        )
        assert isinstance(result, list)
        assert isinstance(total, int)

    asyncio.run(test())