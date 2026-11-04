"""Unit Tests for SHA-256 Calculation, Guardrails, and Deduplication Logic."""

import base64
import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.config import settings
from src.core.errors import InvalidStateError
from src.modules.catalog.application.ingestion_service import IngestionService, compute_sha256
from src.modules.catalog.application.schemas import DocumentIngestRequest
from src.modules.catalog.domain.models import Scheme, SchemeVersion


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

    req = DocumentIngestRequest.model_construct(
        scheme_id="sch-test-01",
        academic_year="2024-2025",
        source_url="https://example.gov.in/invalid.pdf",
        document_content_base64="!!!bad-base64-padding!@#$",
    )

    with pytest.raises(InvalidStateError, match="Failed to decode document_content_base64"):
        await service.ingest_document(req)


@pytest.mark.asyncio
async def test_ingestion_service_oversized_file_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify IngestionService rejects files exceeding MAX_INGESTION_FILE_SIZE_BYTES."""
    mock_session = AsyncMock()
    service = IngestionService(mock_session)

    monkeypatch.setattr(settings, "MAX_INGESTION_FILE_SIZE_BYTES", 50)

    # 100 bytes of content
    big_doc = b"%PDF-1.4 " + (b"A" * 80) + b" %%EOF"
    req = DocumentIngestRequest.model_construct(
        scheme_id="sch-test-01",
        academic_year="2024-2025",
        source_url="https://example.gov.in/oversized.pdf",
        document_content_base64=base64.b64encode(big_doc).decode("utf-8"),
    )

    with pytest.raises(InvalidStateError, match="exceeds maximum allowed size"):
        await service.ingest_document(req)


@pytest.mark.asyncio
async def test_ingestion_service_magic_bytes_check() -> None:
    """Verify IngestionService requires standard '%PDF-' magic bytes header."""
    mock_session = AsyncMock()
    service = IngestionService(mock_session)

    non_pdf = b"NOT_A_PDF_DOCUMENT_CONTENT %%EOF"
    req = DocumentIngestRequest.model_construct(
        scheme_id="sch-test-01",
        academic_year="2024-2025",
        source_url="https://example.gov.in/fake.pdf",
        document_content_base64=base64.b64encode(non_pdf).decode("utf-8"),
    )

    with pytest.raises(InvalidStateError, match="Missing standard '%PDF-' magic bytes header"):
        await service.ingest_document(req)


@pytest.mark.asyncio
async def test_ingestion_service_missing_eof_check() -> None:
    """Verify IngestionService requires standard '%%EOF' trailer marker."""
    mock_session = AsyncMock()
    service = IngestionService(mock_session)

    truncated_pdf = b"%PDF-1.4 Valid Header but truncated before end of file marker..."
    req = DocumentIngestRequest.model_construct(
        scheme_id="sch-test-01",
        academic_year="2024-2025",
        source_url="https://example.gov.in/truncated.pdf",
        document_content_base64=base64.b64encode(truncated_pdf).decode("utf-8"),
    )

    with pytest.raises(InvalidStateError, match="Missing standard PDF '%%EOF' marker"):
        await service.ingest_document(req)


@pytest.mark.asyncio
async def test_ingestion_service_cross_scheme_reuse() -> None:
    """Verify IngestionService recognizes cross-scheme shared document sources."""
    mock_session = AsyncMock()
    service = IngestionService(mock_session)

    # Valid PDF
    doc = b"%PDF-1.4 Umbrella Ministry Guidelines 2024-2025 %%EOF"
    sha = hashlib.sha256(doc).hexdigest()

    mock_scheme = MagicMock(spec=Scheme)
    mock_other_ver = MagicMock(spec=SchemeVersion)
    mock_other_ver.scheme_id = "sch-other-01"

    # Mock repository
    service.repo.get_by_id = AsyncMock(return_value=mock_scheme)  # type: ignore[method-assign]

    # Same scheme has none, but another scheme has it
    async def mock_get_by_sha(_h: str, scheme_id: str | None = None) -> SchemeVersion | None:
        if scheme_id == "sch-my-01":
            return None
        return mock_other_ver

    service.repo.get_version_by_sha256 = AsyncMock(side_effect=mock_get_by_sha)  # type: ignore[method-assign]
    service.repo.get_next_version_number = AsyncMock(return_value=1)  # type: ignore[method-assign]
    service.repo.create_version = AsyncMock()  # type: ignore[method-assign]

    req = DocumentIngestRequest.model_construct(
        scheme_id="sch-my-01",
        academic_year="2024-2025",
        source_url="https://example.gov.in/umbrella.pdf",
        document_content_base64=base64.b64encode(doc).decode("utf-8"),
    )

    res = await service.ingest_document(req)
    assert res.is_duplicate is False
    assert res.deduplication_status == "NEW_VERSION_REUSED_SOURCE"
    assert res.content_sha256 == sha
