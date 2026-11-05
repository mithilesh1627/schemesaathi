# SchemeSaathi (स्कीम साथी / ꯁ꯭ꯀꯤꯝ ꯁꯥꯊꯤ)

> **Intelligent Multilingual Indian Government Scholarship Discovery Platform**  
> *Initial Strategic Focus: Manipur & Indian Central Government Scholarships*

---

## Milestone M0: Research, Architecture, Schemas & Formal Specification

Milestone M0 establishes the complete theoretical, architectural, statutory, and security foundations for **SchemeSaathi**. All specifications are documented with zero synthetic data and verified against official government portals (`scholarships.gov.in`, `myscheme.gov.in`, `tahmanipur.gov.in`, `manipurobcsc.mn.gov.in`, `highereducationmanipur.gov.in`, `tribal.nic.in`, `socialjustice.gov.in`, `education.gov.in`, `aicte-india.org`).

---

## Milestone M1: Modular Monolith Implementation

### Sprint 1: Backend Foundation, Schema Migrations, Ingestion & Hardening
- **Status:** **SIGNED OFF & READY FOR SPRINT 2** (Git Commit `467703c`)
- **Implemented Capabilities:**
  - Python 3.12 FastAPI modular monolith architecture with Domain-Driven Design (DDD) module boundaries.
  - SQLAlchemy 2.0 Async, asyncpg, and Alembic migrations targeting PostgreSQL 16 + pgvector.
  - Reversible database migrations (`0001_initial_m0_schema.py` and `0002_add_document_storage_fields.py`).
  - Liveness (`/health/live`) and readiness (`/health/ready`) probes verifying live PostgreSQL and Redis pools.
  - Immutable document ingestion storage (`LocalStorageBackend`) with temporary atomic `.tmp` writes, fsync, atomic rename, and read-back SHA-256 verification.
  - Strict upload limits: 15 MB HTTP middleware cap, 14 MB base64 string schema limit, 10 MB decoded byte limit with consistent HTTP 413 responses.
  - Administrative authentication (`X-Admin-API-Key` / `Authorization: Bearer`) and Redis sliding-window write rate limiting (429 with `Retry-After`, 503 fail-closed).
  - Production fail-safe startup: refuses startup if default `SECRET_KEY`, unconfigured `ADMIN_API_KEY`, `DEBUG=True`, `sqlite`, or wildcard `CORS_ORIGINS=["*"]` with credentials are used.
  - Connection pool math: $2\text{ workers} \times (10 + 5) = 30$ max database connections documented and configured.
  - In-flight DPDP Act 2023 privacy protection: unconditional 12-digit Aadhaar sequence redaction (`[REDACTED_AADHAAR]`) and Pydantic validation error sanitization (stripping submitted input payloads from logs and error responses).
  - Multi-version catalog isolation: filtering applies strictly to the latest scheme version (`ROW_NUMBER() OVER (PARTITION BY scheme_id ORDER BY version_number DESC) == 1`) and utilizes PostgreSQL JSONB containment (`@>`) leveraging existing GIN indexes.
  - Production multi-stage Dockerfile with non-root user and verified `--no-cache` builds.
  - CI workflow configured with real PostgreSQL 16 + pgvector on port 5432.
  - **Test Suite:** 86 tests (100% passing, 0 warnings, 0 skips, **97% overall coverage**).
  - **Next Milestone Target:** Sprint 2 — Deterministic Eligibility Evaluation Engine & JSON-Logic AST Interpreter.

---

## Documentation Structure & Deliverables Navigation

### 1. Research & Problem Validation (`docs/research/`)
- [**Problem Validation & Competitor Analysis**](file:///D:/2026/schemesaathi/docs/research/problem_validation_and_competitor_analysis.md)  
  Empirical root-cause analysis of DBT failure modes, demographic mismatches, NPCI payment bridge errors, Manipur conflict realities (displaced students), and a 6-competitor benchmarking matrix.
- [**Source Registry & Data Collection Plan**](file:///D:/2026/schemesaathi/docs/research/source_registry_and_data_collection_plan.md)  
  Comprehensive registry of 17 official central and state portals, ethical scraping boundaries (zero access control crawling, zero PII collection), layout-aware OCR for scanned government orders, and a standardized JSON schema.
- [**Verified Scholarship Candidates Inventory (44 Candidates)**](file:///D:/2026/schemesaathi/docs/research/scholarship_candidates_inventory.md)  
  Exhaustive catalog of 44 verified central and Manipur state scholarships preserving canonical URLs, access dates (Nov 2026), academic years, publication dates, and strict separation between **statutory eligibility** and **application availability**.

### 2. Product & Architecture (`docs/architecture/`)
- [**Product Requirements Document (PRD)**](file:///D:/2026/schemesaathi/docs/architecture/prd.md)  
  User personas (Hill-district ST student, rural OBC student, CSC VLE operator), functional requirements (FR-100 to FR-400), NFRs (sub-150ms evaluation, 120KB payload budget, zero false positives), and acceptance criteria.
- [**Modular Monolith Architecture & Data Flow**](file:///D:/2026/schemesaathi/docs/architecture/modular_monolith_architecture.md)  
  Domain-Driven Design (DDD) with 5 bounded contexts, clean architecture module layout, typed in-memory facades, sequence diagrams for Ingestion and Evaluation, and physical hardware deployment topology.
- [**Database Schema Specification (PostgreSQL + pgvector)**](file:///D:/2026/schemesaathi/docs/architecture/database_schema.md) | [**DDL Script (`database_schema.sql`)**](file:///D:/2026/schemesaathi/docs/architecture/database_schema.sql)  
  Production-grade DDL defining 14 relational tables, B-Tree and GIN indexes on JSON-Logic rules, HNSW index on 1536-dimensional embeddings, and DPDP Act consent tables.
- [**Deterministic Eligibility Engine Design**](file:///D:/2026/schemesaathi/docs/architecture/deterministic_eligibility_engine.md)  
  Why pure LLMs fail at eligibility, mathematical Boolean AST specification, JSON-Logic grammar, decision table solver, partial evaluation solver, and 3 concrete AST examples.
- [**Multilingual Conversational RAG Architecture**](file:///D:/2026/schemesaathi/docs/architecture/rag_design.md)  
  Hierarchical table-preserving chunking (512 tokens), hybrid search (BM25 + pgvector HNSW), cross-encoder reranker, verifiable inline citations `[^1]`, and Manipuri (Meiteilon) dual-script and transliteration NLP strategy.
- [**Security, Privacy & DPDP Compliance Design**](file:///D:/2026/schemesaathi/docs/architecture/security_and_privacy_design.md)  
  Compliance with Digital Personal Data Protection Act 2023, Zero-Aadhaar storage policy, automated in-flight regex scrubber, TLS 1.3, AES-256 at rest, RBAC matrix, and tamper-evident cryptographic hash chaining.

### 3. Architecture Decision Records (`docs/architecture/adr/`)
- [**ADR-001: Modular Monolith Architecture over Microservices**](file:///D:/2026/schemesaathi/docs/architecture/adr/ADR-001-modular-monolith-over-microservices.md)
- [**ADR-002: Deterministic Rule Engine Decoupled from Conversational RAG**](file:///D:/2026/schemesaathi/docs/architecture/adr/ADR-002-deterministic-engine-first-before-rag.md)
- [**ADR-003: Unified Storage with PostgreSQL 16 & pgvector**](file:///D:/2026/schemesaathi/docs/architecture/adr/ADR-003-postgres-pgvector-unified-storage.md)
- [**ADR-004: Multilingual NLP & Transliteration Strategy for Manipuri (Meiteilon)**](file:///D:/2026/schemesaathi/docs/architecture/adr/ADR-004-multilingual-nlp-strategy-for-manipuri.md)
- [**ADR-005: Stateless Guest Evaluations & Zero-Aadhaar DPDP Compliance**](file:///D:/2026/schemesaathi/docs/architecture/adr/ADR-005-stateless-evaluations-and-dpdp-compliance.md)

### 4. API Contracts (`docs/api/`)
- [**OpenAPI 3.1 Specification (`openapi_specification.yaml`)**](file:///D:/2026/schemesaathi/docs/api/openapi_specification.yaml)
- [**API Contracts & Integration Guide**](file:///D:/2026/schemesaathi/docs/api/api_contracts.md)  
  RESTful contracts for scheme catalog, deterministic profile evaluation, conversational multilingual chat, dynamic document checklist generator, and telemetry.

### 5. Evaluation & Roadmap (`docs/evaluation/`)
- [**Evaluation Strategy & Benchmarking Framework**](file:///D:/2026/schemesaathi/docs/evaluation/evaluation_strategy.md)  
  Track A (Deterministic Zero False-Positive testing), Track B (RAG Triad & Meiteilon ChrF++), Track C (Throttled 2G/3G network SLAs), and a 20 canonical student persona golden dataset.
- [**Milestone M0 Acceptance Report & M1 Implementation Roadmap**](file:///D:/2026/schemesaathi/docs/evaluation/m0_acceptance_report_and_m1_roadmap.md)  
  Formal acceptance audit, itemized verification matrix, marked statutory uncertainties and research gaps, and a concrete 10-week, 5-sprint implementation plan for Milestone M1.
