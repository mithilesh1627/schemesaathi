"""Pydantic Schemas for Hybrid Retrieval Search API."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class RetrievalSearchRequest(BaseModel):
    """Payload for public hybrid retrieval search endpoint."""

    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Search query in English, Romanized Meiteilon, Bengali script, or Meetei Mayek.",
        examples=["Post-Matric ST scholarship income limit Manipur"],
    )
    top_k: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum candidate chunks to return (default: 20).",
    )
    state_filter: str | None = Field(
        default=None,
        description="Optional state code to filter schemes (state-agnostic Pan-India guardrail).",
        examples=["MANIPUR"],
    )

    model_config = ConfigDict(extra="forbid")


class ApplicationWindowInfo(BaseModel):
    """Statutory application window dates and closure status."""

    window_open_date: date | None = None
    window_close_date: date | None = None
    portal_status: str
    is_window_closed: bool


class RetrievedChunkResponse(BaseModel):
    """Single retrieved knowledge chunk with full official provenance."""

    chunk_id: uuid.UUID
    scheme_id: str
    version_id: uuid.UUID
    section_title: str
    chunk_content: str
    token_count: int
    page_number: int | None
    source_url: str
    document_sha256: str
    academic_year: str
    application_window: ApplicationWindowInfo
    sparse_rank: int | None
    dense_rank: int | None
    rrf_score: float

    model_config = ConfigDict(from_attributes=True)


class RetrievalSearchResponse(BaseModel):
    """Complete hybrid retrieval search response payload."""

    query: str
    detected_script: str
    expanded_query: str
    transliteration_applied: bool = False
    expanded_acronyms: list[str] = Field(default_factory=list)
    total_results: int
    results: list[RetrievedChunkResponse]
    invented_chunk_count: int = 0
    disclaimer: str

    model_config = ConfigDict(from_attributes=True)
