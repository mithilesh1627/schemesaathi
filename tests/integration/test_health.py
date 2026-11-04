"""Integration Tests for Health and Telemetry Endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_probe(async_client: AsyncClient) -> None:
    """Verify /health/live returns HTTP 200 with alive status."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_probe_healthy(async_client: AsyncClient) -> None:
    """Verify /health/ready returns HTTP 200 when DB and Redis are connected."""
    response = await async_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["database"] == "connected"
    assert data["dependencies"]["redis"] == "connected"


@pytest.mark.asyncio
async def test_readiness_probe_unhealthy(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify /health/ready returns HTTP 503 when a dependency is unreachable."""

    async def mock_unhealthy_db() -> bool:
        return False

    monkeypatch.setattr("src.api.health.check_database_health", mock_unhealthy_db)

    response = await async_client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["dependencies"]["database"] == "unreachable"


@pytest.mark.asyncio
async def test_telemetry_health_endpoint(async_client: AsyncClient) -> None:
    """Verify /api/v1/telemetry/health conforms to M0 OpenAPI schema."""
    response = await async_client.get("/api/v1/telemetry/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["HEALTHY", "DEGRADED"]
    assert "version" in data
    assert "database" in data
    assert "vector_extension" in data
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], int)
