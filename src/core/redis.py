"""Async Redis Client Connection Management."""

import redis.asyncio as aioredis

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """Return or initialize global async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        logger.info("Initialized async Redis client.")
    return _redis_client


async def close_redis() -> None:
    """Close active Redis connections."""
    global _redis_client
    if _redis_client is not None:
        if hasattr(_redis_client, "aclose"):
            await _redis_client.aclose()
        else:
            await _redis_client.close()
        _redis_client = None
        logger.info("Async Redis client closed.")


async def check_redis_health() -> bool:
    """Ping Redis to verify active connectivity."""
    try:
        client = get_redis_client()
        pong = await client.ping()
        return bool(pong)
    except Exception as exc:
        logger.warning("Redis health check failed: %s", str(exc))
        return False
