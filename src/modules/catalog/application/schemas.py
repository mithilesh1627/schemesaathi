"""Pydantic v2 Schemas for Catalog, Sources, and Document Ingestion."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog.domain.enums import (
    PortalWindowStatus,
    SchemeLevel,
    VerificationStatus,
)


class SchemeBase(BaseModel):
    """Base scheme properties."""

    scheme_id: str = Field(..., min_length=4, max_length=64, examples=["sch-mn-001"])
    official_code: str = Field(..., max_length=128, examples=["MANIPUR_STATE_MERIT"])
    title_en: str = Field(..., min_length=3, examples=["State Merit Scholarship Manipur"])
    title_hi: str | None = Field(None, examples=["राज्य योग्यता छात्रवृत्ति मणिपुर"])
    title_mni_beng: str | None = Field(None, examples=["ꯃꯅꯤꯄꯨꯔ ꯁ꯭ꯇꯦꯠ ꯃꯦꯔꯤꯠ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ"])
    title_mni_latn: str | None = Field(None, examples=["Manipur State Merit Scholarship"])
    issuing_level: SchemeLevel = Field(..., examples=[SchemeLevel.STATE_SECTOR])
    ministry_or_department: str = Field(
        ..., examples=["Directorate of University & Higher Education, Manipur"]
    )
    implementing_agency: str = Field(..., examples=["Government of Manipur"])
    canonical_source_url: str = Field(..., examples=["https://highereducationmanipur.gov.in"])
    guidelines_document_url: str = Field(..., examples=["https://scholarships.gov.in"])
    is_active: bool = Field(default=True)


class SchemeCreate(SchemeBase):
    """Payload to register a new scheme."""

    pass


class SchemeSummaryResponse(BaseModel):
    """Condensed scheme summary for catalog listings."""

    model_config = ConfigDict(from_attributes=True)

    scheme_id: str
    official_code: str
    title_en: str
    title_mni_beng: str | None = None
    issuing_level: SchemeLevel
    ministry_or_department: str
    is_active: bool
    latest_academic_year: str | None = None
    portal_status: PortalWindowStatus | None = None
    income_ceiling_annual_inr: float | None = None


class SchemeVersionResponse(BaseModel):
    """Scheme version detail."""

    model_config = ConfigDict(from_attributes=True)

    version_id: uuid.UUID
    version_number: int
    academic_year: str
    guideline_publication_date: date | None = None
    retrieved_at: datetime
    content_sha256: str
    verification_status: VerificationStatus
    verification_notes: str | None = None


class SchemeDetailResponse(SchemeBase):
    """Comprehensive scheme details including active version."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime
    versions: list[SchemeVersionResponse] = []


class PaginatedSchemesResponse(BaseModel):
    """Paginated list of schemes."""

    total: int
    page: int
    limit: int
    items: list[SchemeSummaryResponse]


# Source Registry Schemas
class SourceRegistryItem(BaseModel):
    """Verified official government portal entry."""

    registry_id: str = Field(..., examples=["SRC-MN-01"])
    authority_name: str = Field(
        ..., examples=["Department of Tribal Affairs & Hills (TAH), Manipur"]
    )
    portal_url: str = Field(..., examples=["https://tahmanipur.gov.in"])
    domain_type: str = Field(..., examples=["STATE_PORTAL"])
    schemes_covered: list[str] = Field(default_factory=list)
    update_cadence: str = Field(..., examples=["Monthly / Seasonal"])
    robots_txt_status: str = Field(..., examples=["COMPLIANT_PUBLIC_ONLY"])
    verified_at: str = Field(..., examples=["2026-11-04"])


class SourceRegistryResponse(BaseModel):
    """List of all registered and audited government portals."""

    total_sources: int
    sources: list[SourceRegistryItem]


# Document Ingestion Foundation & SHA-256 Deduplication Schemas
class DocumentIngestRequest(BaseModel):
    """Request payload to ingest an official scheme document."""

    scheme_id: str = Field(..., min_length=4, max_length=64, examples=["sch-mn-005"])
    academic_year: str = Field(..., pattern=r"^20[2-3][0-9]-20[2-3][0-9]$", examples=["2024-2025"])
    source_url: str = Field(..., examples=["https://tahmanipur.gov.in/postmatric-st-2024.pdf"])
    document_content_base64: str = Field(
        ..., min_length=16, description="Base64 encoded PDF / document content"
    )
    guideline_publication_date: date | None = None
    notes: str | None = None


class DocumentIngestResponse(BaseModel):
    """Response detailing SHA-256 calculation and deduplication result."""

    content_sha256: str = Field(
        ..., examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"]
    )
    is_duplicate: bool
    deduplication_status: str = Field(
        ..., examples=["NEW_VERSION_REGISTERED or DUPLICATE_IDENTICAL"]
    )
    scheme_id: str
    version_id: uuid.UUID | None = None
    version_number: int | None = None
    ingested_at: datetime
    message: str
