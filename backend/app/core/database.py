import asyncio
import logging
import re
from typing import Any
import asyncpg
from urllib.parse import quote, urlparse, urlunparse
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

        cleaned = re.sub(r'\[([^\[\]]+)\]', strip_non_ipv6_brackets, url)
        if cleaned == url:
            return url
        parsed = urlparse(cleaned)
        hostname = parsed.hostname or ""
        if not hostname:
            return url
        is_ipv6 = ":" in hostname
        if parsed.port:
            if is_ipv6:
                normalized_host = f"[{hostname}]:{parsed.port}"
            else:
                normalized_host = f"{hostname}:{parsed.port}"
        else:
            if is_ipv6:
                normalized_host = f"[{hostname}]"
            else:
                normalized_host = hostname
        if parsed.username:
            auth = parsed.username
            if parsed.password:
                auth += f":{parsed.password}"
            return urlunparse(parsed._replace(netloc=f"{auth}@{normalized_host}"))
        return urlunparse(parsed._replace(netloc=normalized_host))
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
        connect_kwargs: dict[str, Any] = {"min_size": 1, "max_size": 10}
        if settings.APP_ENV == "production":
            connect_kwargs["ssl"] = True
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
