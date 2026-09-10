import asyncio
import logging
import re
import ssl
from typing import Any
import asyncpg
from urllib.parse import urlparse
from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_loop_id: int | None = None


def _normalize_database_url(url: str) -> str:
    try:
        def strip_non_ipv6_brackets(match: re.Match) -> str:
            inner = match.group(1)
            if ":" in inner:
                return match.group(0)
            return inner

        return re.sub(r'\[([^\[\]]+)\]', strip_non_ipv6_brackets, url)
    except Exception:
        return url


async def get_pool() -> asyncpg.Pool:
    global _pool, _pool_loop_id
    try:
        current_loop = id(asyncio.get_running_loop())
    except RuntimeError:
        current_loop = None

    if _pool is None or _pool_loop_id != current_loop:
        if _pool is not None:
            try:
                await _pool.close()
            except Exception:
                pass
        settings.validate_production()
        database_url = _normalize_database_url(settings.DATABASE_URL)
        try:
            parsed = urlparse(database_url)
            logger.info(
                "DATABASE connection target: host=%s port=%s database=%s user=%s",
                parsed.hostname,
                parsed.port,
                parsed.path.lstrip('/'),
                parsed.username,
            )
        except Exception:
            pass
        connect_kwargs: dict[str, Any] = {"min_size": 1, "max_size": 10, "statement_cache_size": 0}
        if settings.APP_ENV == "production":
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_kwargs["ssl"] = ssl_context
        try:
            _pool = await asyncpg.create_pool(
                database_url,
                **connect_kwargs,
            )
        except Exception as exc:
            logger.error("Failed to create database pool: %s", exc, exc_info=True)
            raise RuntimeError(f"Database connection failed: {exc}") from exc
        _pool_loop_id = current_loop
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
