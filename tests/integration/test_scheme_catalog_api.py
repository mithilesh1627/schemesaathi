"""Integration Tests for Scheme Catalog Endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_scheme(async_client: AsyncClient) -> None:
    """Verify creating a scheme and fetching it by ID."""
    payload = {
        "scheme_id": "sch-mn-test-01",
        "official_code": "MN_TEST_01",
        "title_en": "Manipur Engineering Talent Scholarship",
        "title_hi": "मणिपुर इंजीनियरिंग प्रतिभा छात्रवृत्ति",
        "title_mni_beng": "ꯃꯅꯤꯄꯨꯔ ꯏꯟꯖꯤꯅꯤꯌꯔꯤꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ",
        "issuing_level": "STATE_SECTOR",
        "ministry_or_department": "Directorate of University & Higher Education, Manipur",
        "implementing_agency": "Government of Manipur",
        "canonical_source_url": "https://highereducationmanipur.gov.in",
        "guidelines_document_url": "https://scholarships.gov.in",
        "is_active": True,
    }

    # 1. Create scheme
    create_resp = await async_client.post("/api/v1/schemes/", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["scheme_id"] == "sch-mn-test-01"
    assert created_data["official_code"] == "MN_TEST_01"

    # 2. Fetch scheme by ID
    get_resp = await async_client.get("/api/v1/schemes/sch-mn-test-01")
    assert get_resp.status_code == 200
    detail_data = get_resp.json()
    assert detail_data["scheme_id"] == "sch-mn-test-01"
    assert detail_data["title_en"] == "Manipur Engineering Talent Scholarship"


@pytest.mark.asyncio
async def test_duplicate_scheme_id_rejected(async_client: AsyncClient) -> None:
    """Verify attempting to recreate an existing scheme ID returns HTTP 400."""
    payload = {
        "scheme_id": "sch-mn-dup-test",
        "official_code": "MN_DUP_01",
        "title_en": "Duplicate Test Scheme",
        "issuing_level": "STATE_SECTOR",
        "ministry_or_department": "Education Department",
        "implementing_agency": "State Govt",
        "canonical_source_url": "https://example.gov.in",
        "guidelines_document_url": "https://example.gov.in/doc.pdf",
        "is_active": True,
    }

    resp1 = await async_client.post("/api/v1/schemes/", json=payload)
    assert resp1.status_code == 201

    resp2 = await async_client.post("/api/v1/schemes/", json=payload)
    assert resp2.status_code == 400
    err = resp2.json()
    assert err["error_code"] == "ERR_INVALID_STATE"


@pytest.mark.asyncio
async def test_get_nonexistent_scheme_returns_404(async_client: AsyncClient) -> None:
    """Verify requesting an unknown scheme ID returns HTTP 404."""
    response = await async_client.get("/api/v1/schemes/sch-nonexistent-999")
    assert response.status_code == 404
    err = response.json()
    assert err["error_code"] == "ERR_ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_paginated_catalog_listing(async_client: AsyncClient) -> None:
    """Verify /api/v1/schemes/catalog returns a paginated list with total count."""
    response = await async_client.get("/api/v1/schemes/catalog?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "items" in data
    assert data["page"] == 1
    assert data["limit"] == 10
