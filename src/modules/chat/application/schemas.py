"""Pydantic Schemas for Chat API Requests and Grounded Responses."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.security import redact_pii_text
from src.modules.chat.application.auditor import NPCI_APB_WARNING, OTR_FACE_RD_WARNING


class ChatMessageRequest(BaseModel):
    """Incoming user chat message and optional profile context updates."""

    session_id: str = Field(..., description="Unique session identifier holding state and history.")
    message: str = Field(..., min_length=1, description="User question or statement.")
    profile_updates: dict[str, Any] | None = Field(
        None, description="Optional structured profile facts provided by user or UI."
    )
    documents_have: list[str] | None = Field(
        None, description="List of document names marked as present by the user for auditing."
    )
    scheme_context: str | None = Field(
        None, description="Optional target scheme ID (e.g. SCH-MN-005) for scheme-specific turns."
    )

    @field_validator("message")
    @classmethod
    def sanitize_and_redact_message(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Chat message must not be empty or whitespace only.")
        return redact_pii_text(clean)


class CitationResponse(BaseModel):
    """Verifiable citation linking claim to authentic retrieved chunk."""

    citation_number: int = Field(..., description="Inline citation marker number, e.g. 1 for [^1].")
    chunk_id: str = Field(..., description="UUID of the supporting knowledge chunk.")
    scheme_id: str = Field(..., description="Canonical scheme identifier.")
    section: str = Field(..., description="Document section heading.")
    source_url: str = Field(..., description="Official government portal URL.")
    content_sha256: str = Field(
        ..., description="SHA-256 of the authentic source guideline document."
    )
    academic_year: str = Field(..., description="Academic year stated in guideline.")
    window_close_date: str | None = Field(
        None, description="Application window close date if specified."
    )
    portal_status: str | None = Field(None, description="Portal window status (OPEN or CLOSED).")


class AuditedDocumentItem(BaseModel):
    """Checklist status for an individual statutory document."""

    document_name: str
    status: str = Field(..., description="HAVE, MISSING, or UNKNOWN.")
    reason_or_guidance: str


class DocumentAuditResult(BaseModel):
    """Audit checklist and statutory DBT/NSP warnings."""

    scheme_id: str
    scheme_title: str
    documents: list[AuditedDocumentItem]
    summary_text: str
    npci_apb_warning: str
    otr_face_rd_warning: str


class EligibilityItemResult(BaseModel):
    """Structured deterministic eligibility summary per scheme."""

    scheme_id: str
    scheme_title: str
    status: str
    reason: str
    rule_description: str
    window_status: str | None = None
    status_label: str | None = None


class ChatMessageResponse(BaseModel):
    """Fully grounded response containing answer, citations, and retrieval metrics."""

    session_id: str
    answer: str
    citations: list[CitationResponse] = Field(default_factory=list)
    routed_query: str
    detected_language: str
    fallback_to_english: bool = False
    chunks_retrieved_count: int
    invented_chunk_count: int = 0
    eligibility_results: list[EligibilityItemResult] | None = None
    document_audit: DocumentAuditResult | None = None
    is_refusal: bool = False


class SchemeChecklistDocumentItem(BaseModel):
    """Checklist item for an individual required document derived from guideline chunks."""

    id: str = Field(..., description="Stable identifier / slug for the document.")
    name: str = Field(..., description="Standardized document name.")
    desc: str = Field(..., description="Guidance or extraction source description.")
    status: str = Field(default="UNKNOWN", description="Default status (HAVE, MISSING, UNKNOWN).")
    is_available: bool = Field(
        default=True, description="Whether statutory document list is available from guideline."
    )


class SchemeChecklistResponse(BaseModel):
    """Checklist schema for a scheme exposing DocumentReadinessAuditor derived requirements."""

    scheme_id: str = Field(..., description="Canonical scheme identifier.")
    title: str = Field(..., description="Official scheme title in English.")
    academic_year: str = Field(default="2025-2026", description="Academic year.")
    window_close_date: str | None = Field(None, description="Application window close date.")
    portal_status: str = Field(default="CLOSED", description="Application portal window status.")
    portal_url: str = Field(..., description="Official government application portal URL.")
    documents: list[SchemeChecklistDocumentItem] = Field(default_factory=list)
    has_guideline_documents: bool = Field(
        default=True, description="Whether guideline chunks provide a statutory document list."
    )
    guidance_note: str | None = Field(
        None, description="Notice if document list is not available in guideline."
    )
    npci_apb_warning: str = Field(
        default=NPCI_APB_WARNING, description="Mandatory NPCI APB warning."
    )
    otr_face_rd_warning: str = Field(
        default=OTR_FACE_RD_WARNING, description="Mandatory NSP OTR / Face RD warning."
    )
