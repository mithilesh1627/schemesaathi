"""Integration and Unit Tests for Error Sanitization and PII Redaction (Work Item R6)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.errors import sanitize_validation_errors
from src.core.security import (
    redact_aadhaar_pii,
    validate_verhoeff,
)
from src.main import app


def test_verhoeff_algorithm_correctness() -> None:
    """Verify Verhoeff check digit validation distinguishes valid from invalid numbers."""
    # Known valid Aadhaar numbers passing Verhoeff checksum
    assert validate_verhoeff("999988887779") is True
    assert validate_verhoeff("9999 8888 7779") is True
    assert validate_verhoeff("9999-8888-7779") is True

    # Invalid numbers failing Verhoeff checksum
    assert validate_verhoeff("999988887770") is False  # wrong check digit
    assert validate_verhoeff("123456789012") is False
    assert validate_verhoeff("234567890120") is False
    assert validate_verhoeff("12345") is False  # Length != 12


def test_unconditional_aadhaar_redaction() -> None:
    """Verify redaction is UNCONDITIONAL under Zero-Aadhaar policy.

    Even if a 12-digit number has a checksum typo or fails Verhoeff,
    it must be aggressively redacted from logs, errors, and responses.
    """
    invalid_verhoeff = "1234 5678 9012"
    valid_verhoeff = "9999 8888 7779"
    hyphenated = "9999-8888-7779"
    raw_12 = "111122223333"

    assert (
        redact_aadhaar_pii(f"Citizen id is {invalid_verhoeff}")
        == "Citizen id is [REDACTED_AADHAAR]"
    )
    assert redact_aadhaar_pii(f"Aadhaar: {valid_verhoeff}") == "Aadhaar: [REDACTED_AADHAAR]"
    assert redact_aadhaar_pii(f"Reference: {hyphenated}") == "Reference: [REDACTED_AADHAAR]"
    assert redact_aadhaar_pii(f"Digits: {raw_12}") == "Digits: [REDACTED_AADHAAR]"


def test_sanitize_validation_errors_strips_input_payload() -> None:
    """Verify Pydantic validation error objects have 'input' field stripped."""
    mock_pydantic_errors = [
        {
            "type": "string_too_long",
            "loc": ("body", "document_content_base64"),
            "msg": "String should have at most 14000000 characters",
            "input": "SENSITIVE_OR_HUGE_PAYLOAD_CONTENT_THAT_MUST_NOT_BE_EXPOSED",
            "ctx": {"max_length": 14000000, "input": "LEAKED_INPUT"},
        },
        {
            "type": "value_error",
            "loc": ("body", "title_en"),
            "msg": "Aadhaar number 1234 5678 9012 is prohibited",
            "input": "1234 5678 9012",
        },
    ]

    sanitized = sanitize_validation_errors(mock_pydantic_errors)
    assert len(sanitized) == 2

    # Check first error
    assert "input" not in sanitized[0]
    assert sanitized[0]["loc"] == ["body", "document_content_base64"]
    assert sanitized[0]["msg"] == "String should have at most 14000000 characters"
    assert "ctx" in sanitized[0]
    assert "input" not in sanitized[0]["ctx"]
    assert sanitized[0]["ctx"]["max_length"] == 14000000

    # Check second error has unconditional PII redaction in message and input stripped
    assert "input" not in sanitized[1]
    assert sanitized[1]["msg"] == "Aadhaar number [REDACTED_AADHAAR] is prohibited"


@pytest.mark.asyncio
async def test_api_validation_error_does_not_leak_submitted_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify HTTP 422 error response omits submitted input payload and redacts PII."""
    from unittest.mock import AsyncMock

    secret_marker = "SUPER_SECRET_PAYLOAD_MARKER_98765"
    test_12_digit_invalid = "9876 5432 1098"
    admin_token = "test-admin-secret-key-32charslong!"

    from src.core.config import settings

    monkeypatch.setattr(settings, "ADMIN_API_KEY", admin_token)

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    monkeypatch.setattr("src.core.dependencies.get_redis_client", lambda: mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Submit invalid JSON payload to scheme creation endpoint
        response = await client.post(
            "/api/v1/schemes/",
            headers={"X-Admin-API-Key": admin_token},
            json={
                "official_code": secret_marker,
                # Missing required title_en, issuing_level, etc.
                "additional_bogus_field": test_12_digit_invalid,
            },
        )

        assert response.status_code == 422
        data = response.json()
        raw_response_text = response.text

        # The error response must NOT contain the secret payload marker as an 'input' field dump
        for detail in data.get("details", []):
            assert "input" not in detail

        # Any 12-digit number in error messages must be redacted
        assert test_12_digit_invalid not in raw_response_text
