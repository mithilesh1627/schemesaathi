"""Unit Tests for SHA-256 Calculation and Deduplication Logic."""

import base64
import hashlib
from unittest.mock import AsyncMock

import pytest

from src.core.errors import InvalidStateError
from src.modules.catalog.application.ingestion_service import IngestionService, compute_sha256
from src.modules.catalog.application.schemas import DocumentIngestRequest


def test_compute_sha256_known_vector() -> None:
    """Verify compute_sha256 matches hashlib standard digest."""
    test_data = b"Government of Manipur Post-Matric Scholarship 2024-2025"
    expected = hashlib.sha256(test_data).hexdigest()
    actual = compute_sha256(test_data)
    assert actual == expected
    assert len(actual) == 64


def test_compute_sha256_deterministic() -> None:
    """Verify hashing the identical bytes yields exact identical hash."""
    data = b"Test Content for Deduplication Verification"
    hash1 = compute_sha256(data)
    hash2 = compute_sha256(data)
    assert hash1 == hash2


def test_compute_sha256_different_content() -> None:
    """Verify different content produces strictly different hashes."""
    data1 = b"Scholarship Document v1"
    data2 = b"Scholarship Document v2"
    assert compute_sha256(data1) != compute_sha256(data2)


@pytest.mark.asyncio
async def test_ingestion_service_empty_bytes_raises_invalid_state() -> None:
    """Verify IngestionService rejects empty decoded content."""
    mock_session = AsyncMock()
    service = IngestionService(mock_session)

    # Empty base64 payload
    req = DocumentIngestRequest.model_construct(
        scheme_id="sch-test-01",
        academic_year="2024-2025",
        source_url="https://example.gov.in/empty.pdf",
        document_content_base64=base64.b64encode(b"").decode("utf-8"),
    )

    with pytest.raises(InvalidStateError, match="Uploaded document content cannot be empty."):
        await service.ingest_document(req)


@pytest.mark.asyncio
async def test_ingestion_service_invalid_base64_raises_invalid_state() -> None:
    """Verify IngestionService raises error on invalid base64 string."""
    mock_session = AsyncMock()
    service = IngestionService(mock_session)

    # Construct request bypassing Pydantic validation to test service guard
    req = DocumentIngestRequest.model_construct(
        scheme_id="sch-test-01",
        academic_year="2024-2025",
        source_url="https://example.gov.in/invalid.pdf",
        document_content_base64="!!!bad-base64-padding!@#$",
    )

    with pytest.raises(InvalidStateError, match="Failed to decode document_content_base64"):
        await service.ingest_document(req)
