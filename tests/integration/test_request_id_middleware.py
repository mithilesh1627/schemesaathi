"""Integration Tests for Request ID Middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_id_generated_automatically(async_client: AsyncClient) -> None:
    """Verify X-Request-ID is automatically generated if not supplied in request."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    assert len(req_id) >= 16
    assert "X-Response-Time-MS" in response.headers


@pytest.mark.asyncio
async def test_request_id_propagated_from_client(async_client: AsyncClient) -> None:
    """Verify client-supplied X-Request-ID is preserved and echoed in response."""
    custom_id = "test-client-req-uuid-999"
    response = await async_client.get(
        "/health/live",
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
