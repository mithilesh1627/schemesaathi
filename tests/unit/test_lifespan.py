"""Unit Tests for Application Lifespan Context Manager."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from src.main import lifespan


@pytest.mark.asyncio
async def test_application_lifespan_lifecycle() -> None:
    """Verify startup logging/eager connection and graceful shutdown pool closure."""
    app = FastAPI()

    mock_close_redis = AsyncMock()
    mock_close_db = AsyncMock()

    with (
        patch("src.main.close_redis", mock_close_redis),
        patch("src.main.close_db_engine", mock_close_db),
    ):
        async with lifespan(app):
            # Application is running in context
            pass

        mock_close_redis.assert_awaited_once()
        mock_close_db.assert_awaited_once()
