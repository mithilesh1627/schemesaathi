"""Integration Tests for Document Ingestion Foundation & SHA-256 Deduplication."""

import base64

import pytest
from httpx import AsyncClient


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
