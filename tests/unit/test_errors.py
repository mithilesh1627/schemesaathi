"""Unit Tests for Domain Exceptions and Error Handlers."""

from src.core.errors import (
    DuplicateDocumentError,
    EntityNotFoundError,
    SchemeSaathiError,
    build_error_response,
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
