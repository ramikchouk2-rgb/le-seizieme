import asyncio
import asyncpg
from app.core.config import settings

_pool: asyncpg.Pool | None = None
_pool_loop_id: int | None = None


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
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=1,
            max_size=10,
        )
        _pool_loop_id = current_loop
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
