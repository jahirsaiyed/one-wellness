from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis() -> Redis:
    return Redis(connection_pool=get_pool())


async def ping_redis() -> bool:
    try:
        r = get_redis()
        return await r.ping()
    except Exception:
        return False
