"""Integration Tests for Administrative Authorization and Write Rate Limiting (Work Item R4)."""

import base64
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db_session
from src.main import create_app

VALID_ADMIN_KEY = "test-admin-secret-key-configured-32c"


@pytest.fixture
def auth_test_app(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Create test application instance with configured admin key."""
    monkeypatch.setattr(settings, "ADMIN_API_KEY", VALID_ADMIN_KEY)
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 5)

    # Health check mocks
    async def mock_redis_health() -> bool:
        return True

    async def mock_db_health() -> bool:
        return True

    monkeypatch.setattr("src.api.health.check_redis_health", mock_redis_health)
    monkeypatch.setattr("src.api.health.check_database_health", mock_db_health)

    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    return app


@pytest.mark.asyncio
async def test_write_endpoints_unauthenticated_returns_401(auth_test_app: FastAPI) -> None:
    """Verify write endpoints return HTTP 401 when no credentials are provided."""
    transport = ASGITransport(app=auth_test_app)
    # No auth headers
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. POST /api/v1/schemes/
        scheme_payload = {
            "scheme_id": "sch-auth-test-01",
            "official_code": "AUTH_TEST_01",
            "title_en": "Auth Test Scheme",
            "issuing_level": "STATE_SECTOR",
            "ministry_or_department": "Dept of Education",
            "implementing_agency": "Govt of Manipur",
            "canonical_source_url": "https://example.gov.in",
            "guidelines_document_url": "https://example.gov.in/doc.pdf",
            "is_active": True,
        }
        resp1 = await client.post("/api/v1/schemes/", json=scheme_payload)
        assert resp1.status_code == 401
        assert resp1.json()["error_code"] == "ERR_UNAUTHENTICATED"
        assert "WWW-Authenticate" in resp1.headers

        # 2. POST /api/v1/ingest/document
        doc_payload = {
            "scheme_id": "sch-auth-test-01",
            "academic_year": "2024-2025",
            "source_url": "https://example.gov.in/doc.pdf",
            "document_content_base64": base64.b64encode(b"%PDF-1.4 test %%EOF").decode("utf-8"),
        }
        resp2 = await client.post("/api/v1/ingest/document", json=doc_payload)
        assert resp2.status_code == 401
        assert resp2.json()["error_code"] == "ERR_UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_write_endpoints_wrong_credentials_returns_403(auth_test_app: FastAPI) -> None:
    """Verify write endpoints return HTTP 403 when wrong API key is provided."""
    transport = ASGITransport(app=auth_test_app)
    wrong_headers = {"X-Admin-API-Key": "completely-wrong-invalid-secret-key"}

    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=wrong_headers
    ) as client:
        scheme_payload = {
            "scheme_id": "sch-auth-test-02",
            "official_code": "AUTH_TEST_02",
            "title_en": "Auth Test Scheme 2",
            "issuing_level": "STATE_SECTOR",
            "ministry_or_department": "Dept of Education",
            "implementing_agency": "Govt of Manipur",
            "canonical_source_url": "https://example.gov.in",
            "guidelines_document_url": "https://example.gov.in/doc.pdf",
            "is_active": True,
        }
        resp1 = await client.post("/api/v1/schemes/", json=scheme_payload)
        assert resp1.status_code == 403
        assert resp1.json()["error_code"] == "ERR_FORBIDDEN"

        # Also test Bearer token format with wrong token
        bearer_wrong_headers = {"Authorization": "Bearer completely-wrong-invalid-secret-key"}
        resp2 = await client.post(
            "/api/v1/schemes/", json=scheme_payload, headers=bearer_wrong_headers
        )
        assert resp2.status_code == 403
        assert resp2.json()["error_code"] == "ERR_FORBIDDEN"


@pytest.mark.asyncio
async def test_write_endpoints_correct_credentials_succeeds(
    auth_test_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify write endpoints succeed with valid X-Admin-API-Key and Authorization: Bearer."""
    # Mock Redis rate limiter to succeed
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    monkeypatch.setattr("src.core.dependencies.get_redis_client", lambda: mock_redis)

    transport = ASGITransport(app=auth_test_app)
    valid_headers = {"X-Admin-API-Key": VALID_ADMIN_KEY}

    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=valid_headers
    ) as client:
        scheme_payload = {
            "scheme_id": "sch-auth-success-01",
            "official_code": "AUTH_SUCCESS_01",
            "title_en": "Auth Success Scheme",
            "issuing_level": "STATE_SECTOR",
            "ministry_or_department": "Dept of Education",
            "implementing_agency": "Govt of Manipur",
            "canonical_source_url": "https://example.gov.in",
            "guidelines_document_url": "https://example.gov.in/doc.pdf",
            "is_active": True,
        }
        resp = await client.post("/api/v1/schemes/", json=scheme_payload)
        assert resp.status_code == 201
        assert resp.json()["scheme_id"] == "sch-auth-success-01"

    # Also verify Bearer token format works
    bearer_headers = {"Authorization": f"Bearer {VALID_ADMIN_KEY}"}
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=bearer_headers
    ) as client:
        doc_bytes = b"%PDF-1.4 Valid Ingestion with Bearer Auth %%EOF"
        doc_payload = {
            "scheme_id": "sch-auth-success-01",
            "academic_year": "2024-2025",
            "source_url": "https://example.gov.in/doc.pdf",
            "document_content_base64": base64.b64encode(doc_bytes).decode("utf-8"),
        }
        resp_doc = await client.post("/api/v1/ingest/document", json=doc_payload)
        assert resp_doc.status_code == 200
        assert resp_doc.json()["deduplication_status"] == "NEW_VERSION_REGISTERED"


@pytest.mark.asyncio
async def test_unconfigured_admin_key_fails_closed(
    auth_test_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify write endpoints fail closed (HTTP 503) if ADMIN_API_KEY is unset on server."""
    monkeypatch.setattr(settings, "ADMIN_API_KEY", None)

    transport = ASGITransport(app=auth_test_app)
    headers = {"X-Admin-API-Key": "any-submitted-key"}
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        resp = await client.post(
            "/api/v1/schemes/",
            json={"scheme_id": "sch-any", "title_en": "Any"},
        )
        assert resp.status_code == 503
        assert resp.json()["error_code"] == "ERR_SERVICE_UNAVAILABLE"
        assert "ADMIN_API_KEY is unconfigured" in resp.json()["message"]


@pytest.mark.asyncio
async def test_write_rate_limiting_enforcement(
    auth_test_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify exceeding RATE_LIMIT_PER_MINUTE returns HTTP 429 with Retry-After header."""
    mock_redis = AsyncMock()
    # Return count > limit (e.g. 6 when limit is 5)
    mock_redis.incr.return_value = 6
    mock_redis.ttl.return_value = 45
    monkeypatch.setattr("src.core.dependencies.get_redis_client", lambda: mock_redis)

    transport = ASGITransport(app=auth_test_app)
    headers = {"X-Admin-API-Key": VALID_ADMIN_KEY}

    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        resp = await client.post(
            "/api/v1/schemes/",
            json={
                "scheme_id": "sch-rate-test",
                "official_code": "RATE_01",
                "title_en": "Rate Limit Test",
                "issuing_level": "STATE_SECTOR",
                "ministry_or_department": "Dept of Education",
                "implementing_agency": "Govt of Manipur",
                "canonical_source_url": "https://example.gov.in",
                "guidelines_document_url": "https://example.gov.in/doc.pdf",
                "is_active": True,
            },
        )
        assert resp.status_code == 429
        assert resp.json()["error_code"] == "ERR_RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in resp.headers
        assert resp.headers["Retry-After"] == "45"


@pytest.mark.asyncio
async def test_write_fails_closed_when_redis_unavailable(
    auth_test_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify write endpoints fail closed (HTTP 503) if Redis is unreachable."""
    mock_redis = AsyncMock()
    mock_redis.incr.side_effect = ConnectionError("Redis server connection refused")
    monkeypatch.setattr("src.core.dependencies.get_redis_client", lambda: mock_redis)

    transport = ASGITransport(app=auth_test_app)
    headers = {"X-Admin-API-Key": VALID_ADMIN_KEY}

    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        resp = await client.post(
            "/api/v1/schemes/",
            json={
                "scheme_id": "sch-redis-down",
                "official_code": "REDIS_DOWN_01",
                "title_en": "Redis Down Scheme",
                "issuing_level": "STATE_SECTOR",
                "ministry_or_department": "Dept of Education",
                "implementing_agency": "Govt of Manipur",
                "canonical_source_url": "https://example.gov.in",
                "guidelines_document_url": "https://example.gov.in/doc.pdf",
                "is_active": True,
            },
        )
        assert resp.status_code == 503
        assert resp.json()["error_code"] == "ERR_SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_read_endpoints_remain_public(auth_test_app: FastAPI) -> None:
    """Verify catalog and source registry GET endpoints remain accessible without auth."""
    transport = ASGITransport(app=auth_test_app)
    # No headers
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp1 = await client.get("/api/v1/schemes/catalog")
        assert resp1.status_code == 200

        resp2 = await client.get("/api/v1/sources/registry")
        assert resp2.status_code == 200
        assert resp2.json()["total_sources"] >= 6
