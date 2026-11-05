"""Document Ingestion Service with SHA-256 Cryptographic Deduplication."""

import base64
import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.errors import (
    EntityNotFoundError,
    InvalidStateError,
    PayloadTooLargeError,
    StorageError,
)
from src.core.logging import get_logger
from src.core.storage import StorageBackend, get_storage_backend
from src.modules.catalog.application.schemas import (
    DocumentIngestRequest,
    DocumentIngestResponse,
)
from src.modules.catalog.domain.enums import DocumentLifecycleState, VerificationStatus
from src.modules.catalog.domain.models import SchemeVersion
from src.modules.catalog.infrastructure.repositories import SchemeRepository

logger = get_logger(__name__)


def compute_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hex digest of raw binary data."""
    return hashlib.sha256(data).hexdigest()


class IngestionService:
    """Orchestrates document ingestion, hashing, persistence, and deduplication verification."""

    def __init__(self, session: AsyncSession, storage: StorageBackend | None = None) -> None:
        self.session = session
        self.repo = SchemeRepository(session)
        self.storage = storage or get_storage_backend()

    async def ingest_document(self, request: DocumentIngestRequest) -> DocumentIngestResponse:
        """Ingest a policy document with SHA-256 deduplication and security guardrails."""
        # 1. State: RECEIVED
        # Enforce encoded payload length limit before decoding (Work item R2)
        if len(request.document_content_base64) > settings.MAX_ENCODED_DOCUMENT_LENGTH:
            raise PayloadTooLargeError(
                f"Encoded document payload exceeds maximum allowed length of "
                f"{settings.MAX_ENCODED_DOCUMENT_LENGTH} characters "
                f"(received {len(request.document_content_base64)} characters)."
            )

        # 2. Decode base64 document content with strict validation
        try:
            raw_bytes = base64.b64decode(request.document_content_base64, validate=True)
        except Exception as exc:
            raise InvalidStateError(
                message="Failed to decode document_content_base64. Must be valid base64 string.",
                details={"error": str(exc)},
            ) from exc

        if not raw_bytes:
            raise InvalidStateError("Uploaded document content cannot be empty.")

        # 3. State: VALIDATED
        # Enforce decoded file size limit (Work item R2)
        if len(raw_bytes) > settings.MAX_INGESTION_FILE_SIZE_BYTES:
            raise PayloadTooLargeError(
                f"Uploaded document exceeds maximum allowed size of {settings.MAX_INGESTION_FILE_SIZE_BYTES} bytes "
                f"(received {len(raw_bytes)} bytes)."
            )

        # Enforce PDF Magic Bytes Signature
        if not raw_bytes.startswith(b"%PDF-"):
            raise InvalidStateError(
                "Uploaded document is not a valid PDF file. Missing standard '%PDF-' magic bytes header."
            )

        # Enforce structural integrity (minimum size and EOF marker)
        if len(raw_bytes) < 32 or b"%%EOF" not in raw_bytes[-1024:]:
            raise InvalidStateError(
                "Uploaded document appears corrupted or incomplete. Missing standard PDF '%%EOF' marker."
            )

        # 4. Compute cryptographic SHA-256 hash & safe deterministic storage boundary
        content_hash = compute_sha256(raw_bytes)
        storage_rel_path = f"documents/{content_hash[:2]}/{content_hash}.pdf"
        logger.info(
            "Ingesting document for scheme=%s, academic_year=%s, sha256=%s, target_path=%s, size=%d bytes",
            request.scheme_id,
            request.academic_year,
            content_hash,
            storage_rel_path,
            len(raw_bytes),
        )

        # 5. Verify parent scheme exists
        scheme = await self.repo.get_by_id(request.scheme_id)
        if not scheme:
            raise EntityNotFoundError(entity_name="Scheme", entity_id=request.scheme_id)

        # 6. Check for existing identical document hash (Scoped Deduplication)
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
            # Ensure file is persisted on disk even for duplicates
            if not await self.storage.exists(storage_rel_path):
                await self.storage.store(storage_rel_path, raw_bytes)

            return DocumentIngestResponse(
                content_sha256=content_hash,
                is_duplicate=True,
                deduplication_status="DUPLICATE_IDENTICAL",
                scheme_id=existing_same_scheme.scheme_id,
                version_id=existing_same_scheme.version_id,
                version_number=existing_same_scheme.version_number,
                ingested_at=existing_same_scheme.retrieved_at,
                storage_path=existing_same_scheme.storage_path or storage_rel_path,
                byte_size=existing_same_scheme.byte_size or len(raw_bytes),
                lifecycle_state=DocumentLifecycleState.STORED.value,
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

        # 7. Persist exact decoded bytes to storage atomically (Work item R1)
        # Writes to temp location and renames; verifies read-back SHA-256.
        # If storage fails, whole ingestion fails and leaves no orphan file or record.
        try:
            stored_abs_path = await self.storage.store(storage_rel_path, raw_bytes)
            logger.info("Persisted document bytes to %s", stored_abs_path)
        except Exception as exc:
            logger.error(
                "Failed to store document payload for scheme=%s: %s", request.scheme_id, exc
            )
            if isinstance(exc, StorageError):
                raise
            raise StorageError(f"Document persistence failed: {exc}") from exc

        # 8. State: STORED -> Register new version in database
        next_ver_num = await self.repo.get_next_version_number(request.scheme_id)
        new_version = SchemeVersion(
            scheme_id=request.scheme_id,
            version_number=next_ver_num,
            academic_year=request.academic_year,
            guideline_publication_date=request.guideline_publication_date,
            retrieved_at=datetime.now(UTC),
            content_sha256=content_hash,
            storage_path=storage_rel_path,
            byte_size=len(raw_bytes),
            lifecycle_state=DocumentLifecycleState.STORED.value,
            verification_status=VerificationStatus.OFFICIAL_PROVISIONAL,
            verification_notes=request.notes
            or f"Ingested via IngestionService from {request.source_url}",
        )

        try:
            await self.repo.create_version(new_version)
            await self.session.commit()
            await self.session.refresh(new_version)
        except Exception as exc:
            await self.session.rollback()
            # If DB registration fails and document is not reused, clean up storage file
            if existing_any is None:
                await self.storage.delete(storage_rel_path)
            logger.error("Database registration failed for scheme version; rolled back: %s", exc)
            raise

        logger.info(
            "Registered new scheme version id=%s ver=%d for scheme=%s status=%s path=%s",
            new_version.version_id,
            new_version.version_number,
            request.scheme_id,
            dedup_status,
            storage_rel_path,
        )

        return DocumentIngestResponse(
            content_sha256=content_hash,
            is_duplicate=False,
            deduplication_status=dedup_status,
            scheme_id=request.scheme_id,
            version_id=new_version.version_id,
            version_number=new_version.version_number,
            ingested_at=new_version.retrieved_at,
            storage_path=storage_rel_path,
            byte_size=len(raw_bytes),
            lifecycle_state=DocumentLifecycleState.STORED.value,
            message=(
                f"Successfully registered version {new_version.version_number} "
                f"for scheme {request.scheme_id} ({request.academic_year}) "
                f"[{dedup_status}]."
            ),
        )
