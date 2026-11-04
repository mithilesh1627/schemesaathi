"""Document Ingestion Service with SHA-256 Cryptographic Deduplication."""

import base64
import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.errors import EntityNotFoundError, InvalidStateError
from src.core.logging import get_logger
from src.modules.catalog.application.schemas import (
    DocumentIngestRequest,
    DocumentIngestResponse,
)
from src.modules.catalog.domain.enums import VerificationStatus
from src.modules.catalog.domain.models import SchemeVersion
from src.modules.catalog.infrastructure.repositories import SchemeRepository

logger = get_logger(__name__)


def compute_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hex digest of raw binary data."""
    return hashlib.sha256(data).hexdigest()


class IngestionService:
    """Orchestrates document ingestion, hashing, and deduplication verification."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SchemeRepository(session)

    async def ingest_document(self, request: DocumentIngestRequest) -> DocumentIngestResponse:
        """Ingest a policy document with SHA-256 deduplication and security guardrails."""
        # 1. Decode base64 document content with strict validation
        try:
            raw_bytes = base64.b64decode(request.document_content_base64, validate=True)
        except Exception as exc:
            raise InvalidStateError(
                message="Failed to decode document_content_base64. Must be valid base64 string.",
                details={"error": str(exc)},
            ) from exc

        if not raw_bytes:
            raise InvalidStateError("Uploaded document content cannot be empty.")

        # 2. Enforce file size limit
        if len(raw_bytes) > settings.MAX_INGESTION_FILE_SIZE_BYTES:
            raise InvalidStateError(
                f"Uploaded document exceeds maximum allowed size of {settings.MAX_INGESTION_FILE_SIZE_BYTES} bytes "
                f"(received {len(raw_bytes)} bytes)."
            )

        # 3. Enforce PDF Magic Bytes Signature
        if not raw_bytes.startswith(b"%PDF-"):
            raise InvalidStateError(
                "Uploaded document is not a valid PDF file. Missing standard '%PDF-' magic bytes header."
            )

        # 4. Enforce structural integrity (minimum size and EOF marker)
        if len(raw_bytes) < 32 or b"%%EOF" not in raw_bytes[-1024:]:
            raise InvalidStateError(
                "Uploaded document appears corrupted or incomplete. Missing standard PDF '%%EOF' marker."
            )

        # 5. Compute cryptographic SHA-256 hash & safe deterministic storage boundary
        content_hash = compute_sha256(raw_bytes)
        storage_rel_path = f"documents/{content_hash[:2]}/{content_hash}.pdf"
        logger.info(
            "Ingesting document for scheme=%s, academic_year=%s, sha256=%s, target_path=%s",
            request.scheme_id,
            request.academic_year,
            content_hash,
            storage_rel_path,
        )

        # 6. Verify parent scheme exists
        scheme = await self.repo.get_by_id(request.scheme_id)
        if not scheme:
            raise EntityNotFoundError(entity_name="Scheme", entity_id=request.scheme_id)

        # 7. Check for existing identical document hash (Scoped Deduplication)
        existing_same_scheme = await self.repo.get_version_by_sha256(
            content_hash, scheme_id=request.scheme_id
        )
        if existing_same_scheme is not None:
            logger.info(
                "Deduplication match found: SHA-256 %s already exists as version %d for scheme %s",
                content_hash,
                existing_same_scheme.version_number,
                existing_same_scheme.scheme_id,
            )
            return DocumentIngestResponse(
                content_sha256=content_hash,
                is_duplicate=True,
                deduplication_status="DUPLICATE_IDENTICAL",
                scheme_id=existing_same_scheme.scheme_id,
                version_id=existing_same_scheme.version_id,
                version_number=existing_same_scheme.version_number,
                ingested_at=existing_same_scheme.retrieved_at,
                message=(
                    f"Document with identical SHA-256 ({content_hash[:12]}...) "
                    f"already registered for {existing_same_scheme.scheme_id} "
                    f"under academic year {existing_same_scheme.academic_year}. Redundant processing skipped."
                ),
            )

        # Check cross-scheme identical document reuse
        existing_any = await self.repo.get_version_by_sha256(content_hash)
        dedup_status = (
            "NEW_VERSION_REUSED_SOURCE" if existing_any is not None else "NEW_VERSION_REGISTERED"
        )

        # 8. New document detected -> Register new version
        next_ver_num = await self.repo.get_next_version_number(request.scheme_id)
        new_version = SchemeVersion(
            scheme_id=request.scheme_id,
            version_number=next_ver_num,
            academic_year=request.academic_year,
            guideline_publication_date=request.guideline_publication_date,
            retrieved_at=datetime.now(UTC),
            content_sha256=content_hash,
            verification_status=VerificationStatus.OFFICIAL_PROVISIONAL,
            verification_notes=request.notes
            or f"Ingested via IngestionService from {request.source_url}",
        )

        await self.repo.create_version(new_version)
        await self.session.commit()
        await self.session.refresh(new_version)

        logger.info(
            "Registered new scheme version id=%s ver=%d for scheme=%s status=%s",
            new_version.version_id,
            new_version.version_number,
            request.scheme_id,
            dedup_status,
        )

        return DocumentIngestResponse(
            content_sha256=content_hash,
            is_duplicate=False,
            deduplication_status=dedup_status,
            scheme_id=request.scheme_id,
            version_id=new_version.version_id,
            version_number=new_version.version_number,
            ingested_at=new_version.retrieved_at,
            message=(
                f"Successfully registered version {new_version.version_number} "
                f"for scheme {request.scheme_id} ({request.academic_year}) "
                f"[{dedup_status}]."
            ),
        )
