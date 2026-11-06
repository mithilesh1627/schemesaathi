# SchemeSaathi Sprint 3 Remediation Report — Retrieval Layer

**Date:** 2026-11-06  
**Status:** Ready for re-review as a Sprint 3 retrieval build  
**Target Head:** `a4d46b5`  
**Verified CI Run:** [42203781295](https://github.com/mithilesh1627/schemesaathi/actions/runs/42203781295) (All jobs green)  
**Observed Baseline Test Count:** 145 passed (at start of remediation task)  
**Final Test Count:** 155 passed, 0 failed, 93% test coverage  

---

## Executive Summary

Sprint 3 remediation for SchemeSaathi's OCR, multilingual extraction, and hybrid retrieval layer has resolved all three critical blockers and secondary defects identified during the line-by-line review of commit `578aa2e`. The system operates strictly as a deterministic hybrid retrieval layer: no conversational chat, no LLM answer generation, no grounded synthesis, and no hallucinated statutory content.

All statutory guidelines are extracted from authentic source documents on disk and remote portals, chunked with zero table fracturing and hierarchical lineage prefixes, and indexed into PostgreSQL 16 + pgvector using 1024-dimensional dense embeddings (`BAAI/bge-m3`) alongside full-text search (`tsvector` / GIN index with `websearch_to_tsquery`).

The 20 golden personas continue to evaluate with 0 false positives, and the two demo profiles return exact counts of 2/4/0 (non-displaced) and 3/3/0 (displaced, with `SCH-MN-003` flipping on `is_displaced`).

---

## Blocker Remediation Breakdown

### Blocker 1: Guideline Seeding Path (R1)
- **Problem in `578aa2e`:** Statutory guidelines were synthesized at runtime using hardcoded python dictionaries (`OFFICIAL_GUIDELINE_DATA`) and rendered via `reportlab` (`create_statutory_pdf()`), bypassing authentic PDF extraction. Furthermore, `SCH-MN-007` contained an allowance discrepancy.
- **Remediation:**
  - Deleted `OFFICIAL_GUIDELINE_DATA` and `create_statutory_pdf()` from `src/modules/retrieval/application/corpus_seed_service.py`.
  - Removed `reportlab` completely from the statutory corpus seeding pipeline.
  - Rewrote `CorpusSeedService` to ingest official guideline PDFs from `data/storage/documents/` and remote department portals (`tahmanipur.gov.in`, `highereducationmanipur.gov.in`, `manipurobcsc.mn.gov.in`).
  - Text is extracted directly from authentic documents using `DigitalPdfExtractor` and `ScannedPdfOcrExtractor`.
  - Structured tables (such as maintenance allowance slabs for `SCH-MN-005` and `SCH-MN-007`) are extracted and formatted as Markdown tables, preserving atomic table chunks without fracturing.
  - Reconciled `SCH-MN-007` allowance discrepancy: Verified against official Ministry of Social Justice and Empowerment (MoSJE) PM-YASASVI Post-Matric Guidelines that Group 1 Day Scholar allowance is **₹10,000 per annum** (Group 4 is ₹4,000 per annum). Updated `seed_data.py` to `maintenance_allowance_day_scholar_annual_inr = 10000.0`.

### Blocker 2: Scanned OCR Integration (R2)
- **Problem in `578aa2e`:** `ScannedPdfOcrExtractor` did not integrate a production-grade OCR engine and failed to properly redact PII or handle rupee symbol rendering artifacts.
- **Remediation:**
  - Integrated `PaddleOCR` (PP-OCRv4 model) with `pypdfium2` page rendering in `src/modules/retrieval/infrastructure/extractors.py`.
  - Configured `PaddleOCR(ocr_version="PP-OCRv4", enable_mkldnn=False)` to prevent oneDNN PIR CPU crashes on Windows.
  - Added glyph normalization in `DigitalPdfExtractor` converting Helvetica black-square artifacts (`\u25a0`) to the official Rupee symbol (`₹`).
  - Implemented lookaround-based Aadhaar redaction regex `(?<!\d)\d{12}(?!\d)` to ensure unconditional redaction of 12-digit numbers even when OCR outputs strings without word boundaries.
  - Added unit test `tests/unit/test_ocr_extractor.py` verifying real text recovery and Aadhaar number redaction (`[REDACTED_AADHAAR]`). Test executes in ~16s and passes 100%.

### Blocker 3: Embedding Model & Vector Dimension (R3)
- **Problem in `578aa2e`:** Used 384-dimensional `all-MiniLM-L6-v2` with insufficient multilingual capacity for Meitei Mayek / Bengali script and Hindi domain concepts.
- **Remediation:**
  - Upgraded dense embedding architecture to `BAAI/bge-m3` producing 1024-dimensional, L2-normalized vector embeddings.
  - Authored Alembic migration `0003_update_embedding_dimension_to_1024.py`:
    - Safely flushes stale knowledge chunks.
    - Alters `scheme_knowledge_chunks.embedding` column type from `vector(384)` to `vector(1024)`.
    - Creates HNSW index `idx_scheme_knowledge_chunks_embedding_hnsw` using `vector_cosine_ops` (`m=16`, `ef_construction=64`).
    - Creates GIN full-text search index `idx_scheme_knowledge_chunks_fts` on `to_tsvector('english', chunk_content)`.
  - Executed migration successfully against PostgreSQL 16.
  - Verified semantic similarity performance: Paraphrase query achieves cosine similarity of **0.535 - 0.738**, while completely irrelevant nonsense queries score **0.412** and are cleanly rejected by RRF relevance gating.

---

## Secondary Defect Fixes (R4)

1. **SQL Injection Guard & Parameterization:**
   - In `src/modules/retrieval/infrastructure/repositories.py`, replaced raw f-string SQL vector formatting with parameterized queries using `CAST(:vec AS vector)`.
2. **PostgreSQL Full-Text Search (Sparse BM25/FTS):**
   - Configured `to_tsvector('english', c.chunk_content) @@ websearch_to_tsquery('english', :q)` paired with `idx_scheme_knowledge_chunks_fts` GIN index.
3. **State Filter Guardrail:**
   - Applied `state_filter` at SQL query level before `LIMIT` clause in both sparse and dense retrieval queries.
4. **Application Window Closing Check:**
   - In `attach_provenance`, dynamic `date.today() >= window_close` ensures closed application windows are surfaced correctly.
5. **Graceful Handling of Empty / Whitespace Queries:**
   - Empty or whitespace-only queries return HTTP 200 with 0 results and the statutory disclaimer, avoiding database round-trips.

---

## Verification & Golden Dataset Evidence (R5)

### Dynamic `invented_chunk_count`
- `compute_invented_chunk_count` dynamically retrieves the source guideline document for each candidate chunk and computes token lexical overlap. Chunks failing to match at least 70% of meaningful tokens against the source document are flagged.
- Validated via `test_golden_english_query_top5` (`invented_chunk_count == 0`) and `test_artificial_chunk_triggers_invented_chunk_count` (`invented_chunk_count > 0` when synthetic chunk injected).
- Zero hardcoding of `invented_chunk_count` in `router.py`.

### Demo Profiles & Golden Personas
- **Non-displaced Demo Profile:**
  - Input: ST / Manipur / ₹200,000 / Undergraduate / 65.0% marks / non-displaced.
  - Result: **2 Eligible / 4 Not Eligible / 0 Unknown**.
- **Displaced Demo Profile:**
  - Input: ST / Manipur / ₹200,000 / Undergraduate / 65.0% marks / displaced (`is_displaced=True`).
  - Result: **3 Eligible / 3 Not Eligible / 0 Unknown** (`SCH-MN-003` Chief Minister's College Students Rehabilitation correctly flips to Eligible).
- **20 Golden Personas (`tests/integration/test_golden_personas.py`):**
  - All 20 statutory test personas pass with **0 false positives**.

---

## Test Suite & Quality Metrics

```text
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\2026\schemesaathi
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, asyncio-1.4.1.post1, cov-7.1.0
collected 155 items

================= 155 passed, 1 warning in 238.42s (0:03:58) ==================
TOTAL COVERAGE: 93% (2509 stmts, 180 missed)
```

- **Ruff Linter:** `ruff check src tests` -> All checks passed!
- **Ruff Formatter:** `ruff format --check src tests` -> 72 files already formatted!
- **Mypy Type Check:** `mypy src tests` -> Success: no issues found in 72 source files!

---

## Final Review Verdict

**Ready for re-review as a Sprint 3 retrieval build.**
