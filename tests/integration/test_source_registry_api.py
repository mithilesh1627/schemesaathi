"""Integration Tests for Source Registry API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_sources_registry(async_client: AsyncClient) -> None:
    """Verify /api/v1/sources/registry returns verified official government sources."""
    response = await async_client.get("/api/v1/sources/registry")
    assert response.status_code == 200
    data = response.json()

    assert "total_sources" in data
    assert data["total_sources"] >= 14
    assert "sources" in data
    assert len(data["sources"]) == data["total_sources"]

    # Check that Central and Manipur portals are present
    registry_ids = [s["registry_id"] for s in data["sources"]]
    assert "SRC-CEN-01" in registry_ids  # NSP
    assert "SRC-CEN-02" in registry_ids  # myScheme
    assert "SRC-MN-01" in registry_ids  # Manipur Tribal Affairs
    assert "SRC-MN-02" in registry_ids  # Manipur OBC/SC
