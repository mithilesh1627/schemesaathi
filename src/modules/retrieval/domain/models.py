"""Domain Models and Value Objects for Retrieval and Ingestion Pipeline."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class QueryScript(StrEnum):
    """Detected script family of incoming search query."""

    LATIN = "mni-Latn"
    BENGALI = "mni-Beng"
    MEETEI_MAYEK = "mni-Mtei"
    ENGLISH = "en"


@dataclass(frozen=True)
class DocumentExtractionResult:
    """Provenance and metrics for an extracted official guideline document."""

    document_name: str
    source_url: str
    content_sha256: str
    page_count: int
    character_count: int
    extraction_mode: str  # DIGITAL_TEXT, OCR, HTML_PARSER
    raw_text: str
    tables: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class KnowledgeChunk:
    """Table-preserving knowledge chunk enriched with hierarchical lineage."""

    chunk_id: uuid.UUID
    scheme_id: str
    version_id: uuid.UUID
    language_code: str
    section_title: str
    lineage_prefix: str
    chunk_content: str
    token_count: int
    content_sha256: str
    page_number: int | None = None
    chunk_index: int = 0
    is_table: bool = False
    table_markdown: str | None = None


@dataclass
class RetrievalCandidate:
    """Ranked knowledge chunk candidate with complete official provenance."""

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
    window_open_date: date | None
    window_close_date: date | None
    portal_status: str
    is_window_closed: bool
    sparse_rank: int | None = None
    dense_rank: int | None = None
    rrf_score: float = 0.0
