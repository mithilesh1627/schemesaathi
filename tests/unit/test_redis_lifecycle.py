"""Unit Tests for Redis Client Lifecycle and Health Checking."""

from unittest.mock import AsyncMock, patch

import pytest

from src.core.redis import check_redis_health, close_redis, get_redis_client


@pytest.mark.asyncio
async def test_redis_lifecycle_and_health() -> None:
    """Verify Redis client initialization, ping verification, and disposal."""
    await close_redis()

    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    mock_client.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_client):
        # 1. Get client
        client1 = get_redis_client()
        assert client1 is mock_client

        # Re-fetching returns cached client
        client2 = get_redis_client()
        assert client2 is client1

        # 2. Health check healthy
        is_healthy = await check_redis_health()
        assert is_healthy is True
        mock_client.ping.assert_awaited_once()

        # 3. Close client
        await close_redis()
        mock_client.aclose.assert_awaited_once()

        # Calling close again is idempotent
        await close_redis()


@pytest.mark.asyncio
async def test_redis_health_failure() -> None:
    """Verify check_redis_health handles connection errors gracefully."""
    await close_redis()

    mock_client = AsyncMock()
    mock_client.ping.side_effect = ConnectionError("Redis server unreachable")

    with patch("redis.asyncio.from_url", return_value=mock_client):
        is_healthy = await check_redis_health()
        assert is_healthy is False

    await close_redis()
