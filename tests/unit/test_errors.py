"""Unit Tests for Domain Exceptions and Error Handlers."""

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from src.core.errors import (
    DuplicateDocumentError,
    EntityNotFoundError,
    InvalidStateError,
    SchemeSaathiError,
    ServiceUnavailableError,
    StatutoryRuleValidationError,
    build_error_response,
    register_exception_handlers,
)


def test_scheme_saathi_error_defaults() -> None:
    """Verify base domain error attributes."""
    err = SchemeSaathiError("Base error occurred", error_code="ERR_BASE", status_code=500)
    assert err.message == "Base error occurred"
    assert err.error_code == "ERR_BASE"
    assert err.status_code == 500


def test_entity_not_found_error() -> None:
    """Verify EntityNotFoundError formatting."""
    err = EntityNotFoundError(entity_name="Scheme", entity_id="sch-999")
    assert err.status_code == 404
    assert err.error_code == "ERR_ENTITY_NOT_FOUND"
    assert "sch-999" in err.message
    assert err.details["entity_name"] == "Scheme"


def test_duplicate_document_error() -> None:
    """Verify DuplicateDocumentError formatting."""
    err = DuplicateDocumentError(sha256_hash="abc123hash", existing_id="sch-001")
    assert err.status_code == 409
    assert err.error_code == "ERR_DUPLICATE_DOCUMENT"
    assert "abc123hash" in err.message


def test_invalid_state_error() -> None:
    """Verify InvalidStateError formatting."""
    err = InvalidStateError("Invalid transition state", details={"step": "verify"})
    assert err.status_code == 400
    assert err.error_code == "ERR_INVALID_STATE"
    assert err.details == {"step": "verify"}


def test_statutory_rule_validation_error() -> None:
    """Verify StatutoryRuleValidationError formatting."""
    err = StatutoryRuleValidationError("Invalid AST rule", details={"clause": "income"})
    assert err.status_code == 422
    assert err.error_code == "ERR_STATUTORY_RULE_INVALID"
    assert err.details == {"clause": "income"}


def test_service_unavailable_error() -> None:
    """Verify ServiceUnavailableError formatting."""
    err = ServiceUnavailableError("PostgreSQL")
    assert err.status_code == 503
    assert err.error_code == "ERR_SERVICE_UNAVAILABLE"
    assert "PostgreSQL" in err.message


def test_build_error_response() -> None:
    """Verify build_error_response outputs correct JSON and status."""
    resp = build_error_response(
        status_code=400,
        error_code="ERR_TEST",
        message="Test message",
        details={"field": "test"},
    )
    assert resp.status_code == 400
    assert b"ERR_TEST" in resp.body
    assert b"Test message" in resp.body


@pytest.mark.asyncio
async def test_exception_handlers_integration() -> None:
    """Verify that registered exception handlers intercept HTTP and unhandled exceptions."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/trigger-http-error")
    async def trigger_http_error() -> None:
        raise HTTPException(status_code=403, detail="Forbidden statutory access")

    @app.get("/trigger-unhandled")
    async def trigger_unhandled() -> None:
        raise RuntimeError("Unexpected internal crash")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test HTTP Exception handling
        resp1 = await client.get("/trigger-http-error")
        assert resp1.status_code == 403
        data1 = resp1.json()
        assert data1["error_code"] == "ERR_HTTP_403"
        assert data1["message"] == "Forbidden statutory access"

        # 2. Test Unhandled Exception handling
        resp2 = await client.get("/trigger-unhandled")
        assert resp2.status_code == 500
        data2 = resp2.json()
        assert data2["error_code"] == "ERR_INTERNAL_SERVER_ERROR"
        assert "internal server error" in data2["message"].lower()
