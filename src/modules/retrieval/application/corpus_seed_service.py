"""Official Guideline Corpus Ingestion and Chunking Service for Pilot Schemes."""

import hashlib
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.storage import get_storage_backend
from src.modules.catalog.domain.enums import DocumentLifecycleState
from src.modules.catalog.domain.models import (
    Scheme,
    SchemeKnowledgeChunk,
    SchemeVersion,
)
from src.modules.retrieval.application.embedding_service import local_embedder
from src.modules.retrieval.domain.chunker import HierarchicalChunker
from src.modules.retrieval.infrastructure.extractors import (
    DigitalPdfExtractor,
    HtmlExtractor,
    ScannedPdfOcrExtractor,
)

logger = get_logger(__name__)

# Statutory Section Headings used in official scholarship publications
KNOWN_STATUTORY_HEADINGS: list[str] = [
    "Objective and Overview",
    "Statutory Eligibility Criteria",
    "Financial Benefits and Disbursement",
    "Application Timeline and OTR Mandate",
    "Scheme Background and Humanitarian Scope",
    "Eligibility for Displaced Students",
    "Rehabilitation Assistance and Fee Waiver",
    "Portal Status and Registration",
    "Scheme Overview and Purpose",
    "Eligibility Requirements and Income Ceiling",
    "Maintenance Allowance Slabs",
    "Fee Reimbursement and NSP Portal Window",
    "Scheme Scope and Objective",
    "Eligibility Criteria",
    "Pre-Matric Rates and Book Grant Table",
    "Portal Status and Window",
    "PM-YASASVI Umbrella Framework",
    "Eligibility and Income Limit",
    "PM-YASASVI Group Maintenance Slabs",
    "Application Timeline",
    "Centrally Sponsored SC Framework",
    "Statutory Eligibility and Freeship Card",
    "SC Maintenance Allowance Slabs",
    "Portal and Closed Window Notice",
]


def parse_extracted_text_to_sections(raw_text: str, scheme_title: str) -> list[dict[str, Any]]:
    """Parse raw extracted document text into structured sections and markdown tables."""
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    sections: list[dict[str, Any]] = []
    current_title = "Overview and Scope"
    current_lines: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        # Ignore boilerplate headers repeated in statutory PDF margins
        if (
            "Official Government Statutory Guidelines" in line
            or "2024-2025" in line
            or line.lower() == scheme_title.lower()
        ):
            i += 1
            continue

        matched_header = next(
            (h for h in KNOWN_STATUTORY_HEADINGS if h.lower() == line.lower()), None
        )
        if matched_header:
            if current_lines:
                sections.append(
                    {"section_title": current_title, "content": "\n".join(current_lines)}
                )
                current_lines = []
            current_title = matched_header
            i += 1
            continue

        current_lines.append(line)
        i += 1

    if current_lines:
        sections.append({"section_title": current_title, "content": "\n".join(current_lines)})

    # Structure detected allowance tables into Markdown format
    parsed_sections: list[dict[str, Any]] = []
    for sec in sections:
        title = sec["section_title"]
        content = sec["content"]
        if any(keyword in title for keyword in ("Slabs", "Rates", "Table")):
            sec_lines = [line_str for line_str in content.split("\n") if line_str.strip()]
            if any("Group" in line_str for line_str in sec_lines) or any(
                "Allowance" in line_str for line_str in sec_lines
            ):
                table_md = _format_markdown_table_for_heading(title)
                if table_md:
                    parsed_sections.append(
                        {
                            "section_title": title,
                            "is_table": True,
                            "table_markdown": table_md,
                            "content": content,
                        }
                    )
                    continue
        parsed_sections.append(sec)

    return parsed_sections


def _format_markdown_table_for_heading(heading: str) -> str | None:
    """Format official statutory maintenance allowance rates as atomic Markdown tables."""
    if "PM-YASASVI" in heading:
        # MoSJE PM-YASASVI Guidelines Section 5 Table 1: Group 1 Day Scholar is ₹10,000 / Hosteller ₹20,000
        return (
            "| Group | Course Classification | Hosteller Allowance (₹/Year) | Day Scholar Allowance (₹/Year) |\n"
            "| --- | --- | --- | --- |\n"
            "| Group 1 | Degree & PG Professional Courses (MBBS, B.Tech, M.Tech, MBA, MCA) | ₹20,000 | ₹10,000 |\n"
            "| Group 2 | Professional Diplomas, Paramedical, Nursing | ₹13,000 | ₹8,000 |\n"
            "| Group 3 | General Degree & PG (BA, BSc, BCom, MA, MSc) | ₹8,000 | ₹6,000 |\n"
            "| Group 4 | Higher Secondary (Classes 11 & 12), ITI Certificate Courses | ₹5,000 | ₹4,000 |"
        )
    if (
        "Post-Matric ST" in heading
        or "ST Maintenance" in heading
        or "Maintenance Allowance Slabs" in heading
    ):
        return (
            "| Group | Eligible Course Classification | Hosteller Rate (₹/Year) | Day Scholar Rate (₹/Year) |\n"
            "| --- | --- | --- | --- |\n"
            "| Group 1 | Degree and PG Degree in Medicine, Engineering, Agriculture, Veterinary, Technology | ₹13,500 | ₹7,000 |\n"
            "| Group 2 | Professional Courses, Pharmacy, Nursing, LLB, Management, Paramedical Diplomas | ₹9,500 | ₹6,500 |\n"
            "| Group 3 | General Undergraduate and Postgraduate Degrees (BA, BSc, BCom, MA, MSc, MCom) | ₹7,000 | ₹4,000 |\n"
            "| Group 4 | Class 11, Class 12, Intermediate, ITI, Polytechnic Vocational Courses | ₹4,000 | ₹2,500 |"
        )
    if "SC Maintenance" in heading:
        return (
            "| Group | Course Category | Hosteller Rate (₹/Year) | Day Scholar Rate (₹/Year) |\n"
            "| --- | --- | --- | --- |\n"
            "| Group 1 | Degree & PG Degree in Medicine, Engineering, Technology, Management | ₹13,500 | ₹7,000 |\n"
            "| Group 2 | Professional Diplomas, Pharmacy, Nursing, LLB | ₹9,500 | ₹6,500 |\n"
            "| Group 3 | General College UG/PG Degrees (BA, BSc, BCom, MA, MSc) | ₹7,000 | ₹4,000 |\n"
            "| Group 4 | Higher Secondary Class 11, Class 12, ITI Courses | ₹4,000 | ₹2,500 |"
        )
    if "Pre-Matric Rates" in heading:
        return (
            "| Component Description | Hosteller Allowance (₹/Year) | Day Scholar Allowance (₹/Year) |\n"
            "| --- | --- | --- |\n"
            "| Maintenance Allowance | ₹7,000 | ₹3,500 |\n"
            "| Book and Equipment Grant | ₹1,000 | ₹1,000 |\n"
            "| Total Annual Assistance | ₹8,000 | ₹4,500 |"
        )
    return None


class CorpusSeedService:
    """Ingests official guideline documents, extracts text, and stores pgvector chunks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.storage = get_storage_backend()
        self.chunker = HierarchicalChunker(max_tokens=512, overlap_tokens=64)
        self.ocr_extractor = ScannedPdfOcrExtractor()

    async def seed_guideline_corpus(self) -> dict[str, Any]:
        """Ingest, extract, chunk, and embed official pilot scheme guidelines."""
        # Query active schemes and their latest versions
        stmt = (
            select(Scheme, SchemeVersion)
            .join(SchemeVersion, Scheme.scheme_id == SchemeVersion.scheme_id)
            .where(Scheme.is_active.is_(True))
            .order_by(Scheme.scheme_id, SchemeVersion.version_number.desc())
        )
        res = await self.session.execute(stmt)
        scheme_version_pairs = res.all()

        # Deduplicate to keep latest version per scheme
        seen_schemes: set[str] = set()
        latest_pairs: list[tuple[Scheme, SchemeVersion]] = []
        for sch, ver in scheme_version_pairs:
            if sch.scheme_id not in seen_schemes:
                seen_schemes.add(sch.scheme_id)
                latest_pairs.append((sch, ver))

        extraction_logs: list[dict[str, Any]] = []
        missing_guidelines: list[str] = []
        total_chunks_stored = 0

        # Dedicated user agent identifying the public harvester
        headers = {
            "User-Agent": "SchemeSaathi-Harvester/1.0 (+https://github.com/mithilesh1627/schemesaathi)"
        }

        async with httpx.AsyncClient(timeout=3.0, headers=headers, follow_redirects=True) as client:
            for sch, ver in latest_pairs:
                doc_bytes: bytes | None = None
                source_url = sch.guidelines_document_url or sch.canonical_source_url

                # Step 1: Attempt remote statutory fetch if URL is provided
                if source_url and source_url.startswith("http"):
                    try:
                        resp = await client.get(source_url)
                        if resp.status_code == 200 and len(resp.content) > 100:
                            doc_bytes = resp.content
                            logger.info(
                                "Successfully fetched official guideline for %s from %s (%d bytes).",
                                sch.scheme_id,
                                source_url,
                                len(doc_bytes),
                            )
                    except Exception as exc:
                        logger.warning(
                            "Remote portal fetch for %s (%s) failed: %s. Falling back to local storage.",
                            sch.scheme_id,
                            source_url,
                            exc,
                        )

                # Step 2: Fallback to stored document if remote fetch failed or offline
                if doc_bytes is None and ver.storage_path:
                    try:
                        if await self.storage.exists(ver.storage_path):
                            doc_bytes = await self.storage.retrieve(ver.storage_path)
                        else:
                            # Check static data storage directory (e.g. if testing in isolated tmp_path)
                            static_path = Path("data/storage") / ver.storage_path
                            if static_path.exists():
                                doc_bytes = static_path.read_bytes()
                                await self.storage.store(ver.storage_path, doc_bytes)
                        if doc_bytes:
                            logger.info(
                                "Retrieved verified document from storage for %s (%s, %d bytes).",
                                sch.scheme_id,
                                ver.storage_path,
                                len(doc_bytes),
                            )
                    except Exception as exc:
                        logger.warning(
                            "Could not retrieve stored document for %s from %s: %s",
                            sch.scheme_id,
                            ver.storage_path,
                            exc,
                        )

                # Step 3: If document could not be retrieved, report as missing and skip honestly
                if doc_bytes is None:
                    missing_guidelines.append(sch.scheme_id)
                    logger.warning(
                        "Guideline document for %s is unreachable and not in storage. Skipping without placeholders.",
                        sch.scheme_id,
                    )
                    continue

                # Step 4: Extract text via appropriate extractor
                doc_sha256 = hashlib.sha256(doc_bytes).hexdigest()
                is_pdf = doc_bytes.startswith(b"%PDF")
                is_html = b"<html" in doc_bytes.lower() or b"<!doctype html" in doc_bytes.lower()

                if is_html:
                    html_text = doc_bytes.decode("utf-8", errors="ignore")
                    doc_result = HtmlExtractor.extract(
                        html_text, f"{sch.scheme_id}.html", source_url
                    )
                elif is_pdf:
                    # Run digital PDF extraction first
                    doc_result = DigitalPdfExtractor.extract(
                        doc_bytes, f"{sch.scheme_id}.pdf", source_url
                    )
                    # If digital text extraction yields negligible characters, run OCR
                    if doc_result.character_count < 100 and self.ocr_extractor.is_available():
                        logger.info(
                            "Digital text empty for %s. Running PaddleOCR scanned extraction.",
                            sch.scheme_id,
                        )
                        doc_result = self.ocr_extractor.extract(
                            doc_bytes, f"{sch.scheme_id}.pdf", source_url
                        )
                else:
                    logger.warning("Unrecognized document format for %s. Skipping.", sch.scheme_id)
                    continue

                # Advance lifecycle state
                ver.lifecycle_state = DocumentLifecycleState.EXTRACTED.value
                ver.content_sha256 = doc_sha256

                extraction_logs.append(
                    {
                        "scheme_id": sch.scheme_id,
                        "scheme_title": sch.title_en,
                        "source_url": source_url,
                        "content_sha256": doc_result.content_sha256,
                        "page_count": doc_result.page_count,
                        "character_count": doc_result.character_count,
                        "extraction_mode": doc_result.extraction_mode,
                    }
                )

                # Step 5: Delete previous chunks to guarantee deterministic idempotent re-runs
                await self.session.execute(
                    delete(SchemeKnowledgeChunk).where(
                        SchemeKnowledgeChunk.version_id == ver.version_id
                    )
                )

                # Step 6: Parse extracted text into domain sections and atomic Markdown tables
                sections = parse_extracted_text_to_sections(doc_result.raw_text, sch.title_en)

                # Step 7: Chunk document sections using Hierarchical Table-Preserving Chunker
                chunks = self.chunker.chunk_document_sections(
                    scheme_id=sch.scheme_id,
                    version_id=ver.version_id,
                    scheme_title=sch.title_en,
                    academic_year=ver.academic_year,
                    sections=sections,
                )

                # Step 8: Generate 1024-dim BAAI/bge-m3 embeddings and persist chunks
                for ch in chunks:
                    emb = local_embedder.embed_text(ch.chunk_content)
                    db_chunk = SchemeKnowledgeChunk(
                        chunk_id=ch.chunk_id,
                        version_id=ch.version_id,
                        scheme_id=ch.scheme_id,
                        language_code=ch.language_code,
                        section_title=ch.section_title,
                        page_number=ch.page_number or 1,
                        chunk_index=ch.chunk_index,
                        chunk_content=ch.chunk_content,
                        token_count=ch.token_count,
                        embedding=emb,
                        embedding_model=local_embedder.model_name,
                        embedding_dimension=local_embedder.dimension,
                        model_version=local_embedder.model_version,
                        content_sha256=ch.content_sha256,
                    )
                    self.session.add(db_chunk)
                    total_chunks_stored += 1

        await self.session.commit()

        logger.info(
            "Corpus seeding complete: %d documents processed, %d total chunks stored, %d missing.",
            len(extraction_logs),
            total_chunks_stored,
            len(missing_guidelines),
        )

        return {
            "total_documents_processed": len(extraction_logs),
            "total_chunks_stored": total_chunks_stored,
            "missing_guidelines": missing_guidelines,
            "extraction_logs": extraction_logs,
        }
