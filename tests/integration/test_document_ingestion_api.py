"""Integration Tests for Document Ingestion Foundation & SHA-256 Deduplication."""

import base64
import hashlib
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from src.core.errors import StorageError
from src.core.storage import get_storage_backend


@pytest.mark.asyncio
async def test_document_ingestion_and_sha256_deduplication(async_client: AsyncClient) -> None:
    """Verify document ingestion, SHA-256 calculation, and duplicate detection."""
    # 1. Setup a parent scheme first
    scheme_payload = {
        "scheme_id": "sch-ingest-test-01",
        "official_code": "INGEST_TEST_01",
        "title_en": "Ingestion Testing Scheme",
        "issuing_level": "CENTRALLY_SPONSORED",
        "ministry_or_department": "Ministry of Tribal Affairs",
        "implementing_agency": "Govt of Manipur",
        "canonical_source_url": "https://tahmanipur.gov.in",
        "guidelines_document_url": "https://tahmanipur.gov.in/guidelines.pdf",
        "is_active": True,
    }
    create_resp = await async_client.post("/api/v1/schemes/", json=scheme_payload)
    assert create_resp.status_code == 201

    # 2. Ingest document v1 (Valid PDF with magic bytes and EOF)
    doc_content = b"%PDF-1.4 Official Manipur Scholarship Guidelines 2024-25 Content... %%EOF"
    doc_b64 = base64.b64encode(doc_content).decode("utf-8")

    ingest_payload = {
        "scheme_id": "sch-ingest-test-01",
        "academic_year": "2024-2025",
        "source_url": "https://tahmanipur.gov.in/guidelines-2024.pdf",
        "document_content_base64": doc_b64,
        "notes": "Initial verified guideline ingestion",
    }

    resp1 = await async_client.post("/api/v1/ingest/document", json=ingest_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()

    assert data1["is_duplicate"] is False
    assert data1["deduplication_status"] == "NEW_VERSION_REGISTERED"
    assert data1["version_number"] == 1
    assert "content_sha256" in data1
    assert len(data1["content_sha256"]) == 64

    # 3. Ingest exact identical document again -> Must trigger deduplication
    resp2 = await async_client.post("/api/v1/ingest/document", json=ingest_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["is_duplicate"] is True
    assert data2["deduplication_status"] == "DUPLICATE_IDENTICAL"
    assert data2["version_number"] == 1
    assert data2["content_sha256"] == data1["content_sha256"]
    assert "Redundant processing skipped" in data2["message"]

    # 4. Ingest an updated/modified document -> Must create version 2
    doc_content_v2 = (
        b"%PDF-1.4 Official Manipur Scholarship Guidelines 2024-25 REVISED CORRIGENDUM... %%EOF"
    )
    doc_b64_v2 = base64.b64encode(doc_content_v2).decode("utf-8")

    ingest_payload_v2 = {
        "scheme_id": "sch-ingest-test-01",
        "academic_year": "2024-2025",
        "source_url": "https://tahmanipur.gov.in/guidelines-2024-corrigendum.pdf",
        "document_content_base64": doc_b64_v2,
        "notes": "Corrigendum revision",
    }

    resp3 = await async_client.post("/api/v1/ingest/document", json=ingest_payload_v2)
    assert resp3.status_code == 200
    data3 = resp3.json()

    assert data3["is_duplicate"] is False
    assert data3["deduplication_status"] == "NEW_VERSION_REGISTERED"
    assert data3["version_number"] == 2
    assert data3["content_sha256"] != data1["content_sha256"]


@pytest.mark.asyncio
async def test_ingest_document_unknown_scheme_returns_404(async_client: AsyncClient) -> None:
    """Verify attempting to ingest for a non-existent scheme returns HTTP 404."""
    doc_content = b"%PDF-1.4 Unknown Scheme Document %%EOF"
    doc_b64 = base64.b64encode(doc_content).decode("utf-8")

    payload = {
        "scheme_id": "sch-nonexistent-unknown",
        "academic_year": "2024-2025",
        "source_url": "https://example.gov.in/doc.pdf",
        "document_content_base64": doc_b64,
    }

    response = await async_client.post("/api/v1/ingest/document", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "ERR_ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_ingest_document_invalid_magic_bytes_returns_400(async_client: AsyncClient) -> None:
    """Verify non-PDF file signature returns HTTP 400 error."""
    # Create scheme first
    scheme_payload = {
        "scheme_id": "sch-ingest-magic-test",
        "official_code": "MAGIC_TEST_01",
        "title_en": "Magic Bytes Test Scheme",
        "issuing_level": "STATE_SECTOR",
        "ministry_or_department": "Dept of Education",
        "implementing_agency": "Govt of Manipur",
        "canonical_source_url": "https://example.gov.in",
        "guidelines_document_url": "https://example.gov.in/doc.pdf",
        "is_active": True,
    }
    await async_client.post("/api/v1/schemes/", json=scheme_payload)

    # Send executable or image pretending to be document
    fake_content = b"GIF89a Fake Image Content not a valid PDF file at all"
    payload = {
        "scheme_id": "sch-ingest-magic-test",
        "academic_year": "2024-2025",
        "source_url": "https://example.gov.in/fake.pdf",
        "document_content_base64": base64.b64encode(fake_content).decode("utf-8"),
    }

    response = await async_client.post("/api/v1/ingest/document", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "ERR_INVALID_STATE"
    assert "Missing standard '%PDF-' magic bytes header" in data["message"]


@pytest.mark.asyncio
async def test_ingest_document_missing_eof_marker_returns_400(async_client: AsyncClient) -> None:
    """Verify truncated PDF missing %%EOF marker returns HTTP 400 error."""
    scheme_payload = {
        "scheme_id": "sch-ingest-eof-test",
        "official_code": "EOF_TEST_01",
        "title_en": "EOF Test Scheme",
        "issuing_level": "STATE_SECTOR",
        "ministry_or_department": "Dept of Education",
        "implementing_agency": "Govt of Manipur",
        "canonical_source_url": "https://example.gov.in",
        "guidelines_document_url": "https://example.gov.in/doc.pdf",
        "is_active": True,
    }
    await async_client.post("/api/v1/schemes/", json=scheme_payload)

    # Has %PDF- but truncated before %%EOF
    truncated_content = b"%PDF-1.4 Truncated PDF Document that cut off unexpectedly..."
    payload = {
        "scheme_id": "sch-ingest-eof-test",
        "academic_year": "2024-2025",
        "source_url": "https://example.gov.in/truncated.pdf",
        "document_content_base64": base64.b64encode(truncated_content).decode("utf-8"),
    }

    response = await async_client.post("/api/v1/ingest/document", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "ERR_INVALID_STATE"
    assert "Missing standard PDF '%%EOF' marker" in data["message"]


@pytest.mark.asyncio
async def test_ingest_document_invalid_base64_returns_400(async_client: AsyncClient) -> None:
    """Verify invalid base64 string returns HTTP 422 or 400."""
    payload = {
        "scheme_id": "sch-any",
        "academic_year": "2024-2025",
        "source_url": "https://example.gov.in/doc.pdf",
        "document_content_base64": "!!!invalid-base64-string!!!",
    }

    response = await async_client.post("/api/v1/ingest/document", json=payload)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_ingest_document_persists_bytes_and_reads_back(
    async_client: AsyncClient,
) -> None:
    """R1: Verify valid PDF bytes are physically persisted and byte-for-byte identical."""
    scheme_id = "sch-persist-test-01"
    await async_client.post(
        "/api/v1/schemes/",
        json={
            "scheme_id": scheme_id,
            "official_code": "PERSIST_TEST_01",
            "title_en": "Persistence Test Scheme",
            "issuing_level": "STATE_SECTOR",
            "ministry_or_department": "Directorate of Education",
            "implementing_agency": "Govt of Manipur",
            "canonical_source_url": "https://example.gov.in",
            "guidelines_document_url": "https://example.gov.in/doc.pdf",
            "is_active": True,
        },
    )

    doc_bytes = b"%PDF-1.4 Manipur Merit Scholarship Official Document Bytes 2024 %%EOF"
    doc_sha = hashlib.sha256(doc_bytes).hexdigest()
    doc_b64 = base64.b64encode(doc_bytes).decode("utf-8")

    resp = await async_client.post(
        "/api/v1/ingest/document",
        json={
            "scheme_id": scheme_id,
            "academic_year": "2024-2025",
            "source_url": "https://example.gov.in/doc.pdf",
            "document_content_base64": doc_b64,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_sha256"] == doc_sha
    assert data["byte_size"] == len(doc_bytes)
    assert data["lifecycle_state"] == "STORED"
    storage_path = data["storage_path"]
    assert storage_path.endswith(f"{doc_sha}.pdf")

    # Read back from actual storage backend and verify byte-for-byte identity
    storage = get_storage_backend()
    stored_bytes = await storage.retrieve(storage_path)
    assert stored_bytes == doc_bytes
    assert hashlib.sha256(stored_bytes).hexdigest() == doc_sha


@pytest.mark.asyncio
async def test_ingest_duplicate_maintains_single_stored_object(
    async_client: AsyncClient,
) -> None:
    """R1: Verify duplicate submission returns deduplication result and exactly 1 object in storage."""
    scheme_id = "sch-single-storage-test"
    await async_client.post(
        "/api/v1/schemes/",
        json={
            "scheme_id": scheme_id,
            "official_code": "SINGLE_STORE_01",
            "title_en": "Single Storage Test Scheme",
            "issuing_level": "STATE_SECTOR",
            "ministry_or_department": "Directorate of Education",
            "implementing_agency": "Govt of Manipur",
            "canonical_source_url": "https://example.gov.in",
            "guidelines_document_url": "https://example.gov.in/doc.pdf",
            "is_active": True,
        },
    )

    doc_bytes = b"%PDF-1.4 Single Stored Object Test File %%EOF"
    doc_b64 = base64.b64encode(doc_bytes).decode("utf-8")
    payload = {
        "scheme_id": scheme_id,
        "academic_year": "2024-2025",
        "source_url": "https://example.gov.in/doc.pdf",
        "document_content_base64": doc_b64,
    }

    # First ingestion
    resp1 = await async_client.post("/api/v1/ingest/document", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["is_duplicate"] is False

    # Second identical ingestion
    resp2 = await async_client.post("/api/v1/ingest/document", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["is_duplicate"] is True
    assert resp2.json()["deduplication_status"] == "DUPLICATE_IDENTICAL"

    # Verify storage exists and is accessible
    storage = get_storage_backend()
    storage_path = resp1.json()["storage_path"]
    assert await storage.exists(storage_path) is True


@pytest.mark.asyncio
async def test_ingest_storage_failure_fails_closed_and_leaves_no_orphan(
    async_client: AsyncClient,
) -> None:
    """R1: Verify forced storage failure produces error response and leaves no registered record."""
    scheme_id = "sch-fail-store-01"
    await async_client.post(
        "/api/v1/schemes/",
        json={
            "scheme_id": scheme_id,
            "official_code": "FAIL_STORE_01",
            "title_en": "Storage Failure Test Scheme",
            "issuing_level": "STATE_SECTOR",
            "ministry_or_department": "Directorate of Education",
            "implementing_agency": "Govt of Manipur",
            "canonical_source_url": "https://example.gov.in",
            "guidelines_document_url": "https://example.gov.in/doc.pdf",
            "is_active": True,
        },
    )

    doc_bytes = b"%PDF-1.4 Storage Failure Test Document %%EOF"
    doc_b64 = base64.b64encode(doc_bytes).decode("utf-8")

    # Force storage.store to raise StorageError
    with patch(
        "src.core.storage.LocalStorageBackend.store",
        side_effect=StorageError("Simulated disk unwritable / full"),
    ):
        resp = await async_client.post(
            "/api/v1/ingest/document",
            json={
                "scheme_id": scheme_id,
                "academic_year": "2024-2025",
                "source_url": "https://example.gov.in/doc.pdf",
                "document_content_base64": doc_b64,
            },
        )
        assert resp.status_code == 500
        data = resp.json()
        assert data["error_code"] == "ERR_STORAGE_FAILURE"

    # Verify no scheme version was registered for this scheme
    detail_resp = await async_client.get(f"/api/v1/schemes/{scheme_id}")
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["versions"]) == 0


@pytest.mark.asyncio
async def test_ingest_oversized_encoded_payload_rejected_with_413(
    async_client: AsyncClient,
) -> None:
    """R2: Verify oversized encoded payload is rejected with HTTP 413 before decoding."""
    # Construct base64 payload exceeding MAX_ENCODED_DOCUMENT_LENGTH (14,000,000 chars)
    # Using 14,000,100 chars
    oversized_b64 = "A" * 14_000_100

    resp = await async_client.post(
        "/api/v1/ingest/document",
        json={
            "scheme_id": "sch-any",
            "academic_year": "2024-2025",
            "source_url": "https://example.gov.in/doc.pdf",
            "document_content_base64": oversized_b64,
        },
    )
    assert resp.status_code == 413
    data = resp.json()
    assert data["error_code"] == "ERR_PAYLOAD_TOO_LARGE"


@pytest.mark.asyncio
async def test_ingest_oversized_decoded_payload_rejected_with_413(
    async_client: AsyncClient,
) -> None:
    """R2: Verify decoded payload exceeding 10 MB is rejected with HTTP 413."""
    scheme_id = "sch-oversized-decoded-01"
    await async_client.post(
        "/api/v1/schemes/",
        json={
            "scheme_id": scheme_id,
            "official_code": "OVERSIZED_01",
            "title_en": "Oversized Decoded Test Scheme",
            "issuing_level": "STATE_SECTOR",
            "ministry_or_department": "Directorate of Education",
            "implementing_agency": "Govt of Manipur",
            "canonical_source_url": "https://example.gov.in",
            "guidelines_document_url": "https://example.gov.in/doc.pdf",
            "is_active": True,
        },
    )

    # 10 MB + 100 bytes (> 10,485,760 bytes)
    oversized_bytes = b"%PDF-1.4 " + (b"0" * (10 * 1024 * 1024 + 100)) + b" %%EOF"
    oversized_b64 = base64.b64encode(oversized_bytes).decode("utf-8")

    resp = await async_client.post(
        "/api/v1/ingest/document",
        json={
            "scheme_id": scheme_id,
            "academic_year": "2024-2025",
            "source_url": "https://example.gov.in/doc.pdf",
            "document_content_base64": oversized_b64,
        },
    )
    assert resp.status_code == 413
    data = resp.json()
    assert data["error_code"] == "ERR_PAYLOAD_TOO_LARGE"
    assert "exceeds maximum allowed size" in data["message"]
