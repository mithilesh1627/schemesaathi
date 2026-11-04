-- =============================================================================
-- SchemeSaathi Database Schema Specification
-- Dialect: PostgreSQL 16+ with pgvector extension
-- Target Environment: High-Concurrency Modular Monolith
-- Compliance: DPDP Act 2023, Zero Aadhaar Tokenization, Immutable Provenance
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- 1. SCHEME CATALOG & PROVENANCE TABLES
-- =============================================================================

CREATE TYPE scheme_level_enum AS ENUM (
    'CENTRAL_SECTOR',
    'CENTRALLY_SPONSORED',
    'STATE_SECTOR',
    'CORPORATE_CSR_GOVT_PARTNERED'
);

CREATE TYPE verification_status_enum AS ENUM (
    'OFFICIAL_VERIFIED',
    'OFFICIAL_PROVISIONAL',
    'REQUIRES_REVALUATION',
    'DEPRECATED'
);

CREATE TYPE portal_type_enum AS ENUM (
    'NSP_2_0',
    'MYSCHEME',
    'STATE_DIRECT_PORTAL',
    'OFFLINE_INSTITUTE'
);

CREATE TYPE portal_window_status_enum AS ENUM (
    'OPEN',
    'CLOSED',
    'UPCOMING',
    'EXTENDED',
    'UNKNOWN'
);

CREATE TABLE schemes (
    scheme_id VARCHAR(64) PRIMARY KEY, -- e.g. 'sch-mn-001'
    official_code VARCHAR(128) NOT NULL, -- Central or State portal unique identifier
    title_en TEXT NOT NULL,
    title_hi TEXT,
    title_mni_beng TEXT, -- Manipuri in Bengali script
    title_mni_latn TEXT, -- Manipuri Romanized transliteration
    issuing_level scheme_level_enum NOT NULL,
    ministry_or_department VARCHAR(255) NOT NULL,
    implementing_agency VARCHAR(255) NOT NULL,
    canonical_source_url TEXT NOT NULL,
    guidelines_document_url TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE scheme_versions (
    version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scheme_id VARCHAR(64) NOT NULL REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    academic_year VARCHAR(32) NOT NULL, -- e.g. '2024-2025'
    guideline_publication_date DATE,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    content_sha256 CHAR(64) NOT NULL, -- Cryptographic hash of the source PDF/circular
    verification_status verification_status_enum NOT NULL DEFAULT 'OFFICIAL_PROVISIONAL',
    verified_by_user_id VARCHAR(64),
    verification_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_scheme_version UNIQUE (scheme_id, version_number)
);

-- =============================================================================
-- 2. DETERMINISTIC ELIGIBILITY RULES & METADATA
-- =============================================================================

CREATE TABLE scheme_eligibility_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES scheme_versions(version_id) ON DELETE CASCADE,
    -- Fast filter columns for indexing
    income_ceiling_annual_inr NUMERIC(12, 2), -- NULL if no income cap
    minimum_qualifying_marks_percent NUMERIC(5, 2), -- NULL if no marks threshold
    target_categories JSONB NOT NULL DEFAULT '["ALL"]'::jsonb, -- e.g. ["ST", "SC", "OBC"]
    eligible_genders JSONB NOT NULL DEFAULT '["ANY"]'::jsonb, -- ["ANY"] or ["FEMALE"]
    eligible_domiciles JSONB NOT NULL DEFAULT '["ALL_INDIA"]'::jsonb, -- e.g. ["MANIPUR", "NER"]
    eligible_course_levels JSONB NOT NULL, -- e.g. ["UNDERGRADUATE", "POSTGRADUATE"]
    mandates_aishe_institution BOOLEAN NOT NULL DEFAULT TRUE,
    permits_distance_learning BOOLEAN NOT NULL DEFAULT FALSE,
    -- Complete deterministic AST in JSON-Logic standard
    ast_rule_logic JSONB NOT NULL,
    rule_description_en TEXT NOT NULL,
    rule_description_mni TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_version_rule UNIQUE (version_id)
);

CREATE TABLE scheme_application_windows (
    window_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES scheme_versions(version_id) ON DELETE CASCADE,
    portal_type portal_type_enum NOT NULL,
    portal_url TEXT NOT NULL,
    portal_status portal_window_status_enum NOT NULL DEFAULT 'UNKNOWN',
    window_open_date DATE,
    window_close_date DATE,
    defect_verification_close_date DATE,
    institute_verification_close_date DATE,
    requires_otr_face_rd BOOLEAN NOT NULL DEFAULT FALSE,
    requires_freeship_card BOOLEAN NOT NULL DEFAULT FALSE,
    status_last_verified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE scheme_benefits (
    benefit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES scheme_versions(version_id) ON DELETE CASCADE,
    maintenance_allowance_day_scholar_annual_inr NUMERIC(10, 2),
    maintenance_allowance_hosteller_annual_inr NUMERIC(10, 2),
    tuition_fee_coverage_desc TEXT NOT NULL,
    book_and_equipment_grant_annual_inr NUMERIC(10, 2),
    disbursement_mechanism VARCHAR(128) NOT NULL DEFAULT 'DBT_PFMS',
    benefit_summary_en TEXT NOT NULL,
    benefit_summary_hi TEXT,
    benefit_summary_mni TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE scheme_mandatory_documents (
    doc_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES scheme_versions(version_id) ON DELETE CASCADE,
    document_code VARCHAR(64) NOT NULL, -- e.g. 'INCOME_CERT', 'DOMICILE_PRC'
    document_name_en VARCHAR(255) NOT NULL,
    document_name_mni VARCHAR(255),
    issuing_authority_rule TEXT NOT NULL, -- e.g. "SDO / Tehsildar / DC only"
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    validity_duration_months INTEGER, -- e.g. 12 months for income certificates
    critical_validation_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 3. INSTITUTION & AISHE LOOKUP REGISTRY
-- =============================================================================

CREATE TABLE institutes_aishe (
    aishe_code VARCHAR(32) PRIMARY KEY, -- e.g. 'C-12345' or 'U-0123'
    institution_name TEXT NOT NULL,
    institution_type VARCHAR(64) NOT NULL, -- 'CENTRAL_UNIVERSITY', 'STATE_GOVT_COLLEGE', 'IIT', 'NIT'
    state_code VARCHAR(32) NOT NULL, -- e.g. 'MANIPUR'
    district_name VARCHAR(128) NOT NULL,
    is_active_on_nsp BOOLEAN NOT NULL DEFAULT TRUE,
    last_verified_academic_year VARCHAR(32) NOT NULL DEFAULT '2024-2025'
);

-- =============================================================================
-- 4. EVALUATION & STATELESS AUDIT TABLES
-- =============================================================================

CREATE TYPE evaluation_status_enum AS ENUM (
    'ELIGIBLE_NOW',
    'ELIGIBLE_OFF_CYCLE',
    'CONDITIONALLY_ELIGIBLE',
    'INELIGIBLE'
);

CREATE TABLE user_evaluations (
    evaluation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(128) NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Ephemeral profile snapshot used during evaluation (Stateless / DPDP Compliant)
    category_evaluated VARCHAR(32) NOT NULL,
    income_evaluated NUMERIC(12, 2) NOT NULL,
    domicile_evaluated VARCHAR(64) NOT NULL,
    course_level_evaluated VARCHAR(64) NOT NULL,
    marks_percent_evaluated NUMERIC(5, 2),
    gender_evaluated VARCHAR(16),
    is_disability_evaluated BOOLEAN NOT NULL DEFAULT FALSE,
    is_displaced_affected BOOLEAN NOT NULL DEFAULT FALSE,
    total_schemes_checked INTEGER NOT NULL,
    total_eligible INTEGER NOT NULL,
    evaluation_duration_ms INTEGER NOT NULL
);

CREATE TABLE evaluation_rule_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES user_evaluations(evaluation_id) ON DELETE CASCADE,
    scheme_id VARCHAR(64) NOT NULL REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES scheme_versions(version_id) ON DELETE CASCADE,
    evaluation_status evaluation_status_enum NOT NULL,
    passed_income_check BOOLEAN NOT NULL,
    passed_category_check BOOLEAN NOT NULL,
    passed_domicile_check BOOLEAN NOT NULL,
    passed_marks_check BOOLEAN NOT NULL,
    passed_course_check BOOLEAN NOT NULL,
    missing_criteria_fields JSONB, -- Fields required to resolve conditional status
    ineligibility_reasons JSONB, -- Exact statutory reasons for failure
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 5. MULTILINGUAL RAG & VECTOR KNOWLEDGE STORE
-- =============================================================================

CREATE TABLE scheme_knowledge_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES scheme_versions(version_id) ON DELETE CASCADE,
    scheme_id VARCHAR(64) NOT NULL REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    language_code VARCHAR(16) NOT NULL DEFAULT 'en', -- 'en', 'hi', 'mni_beng', 'mni_latn'
    section_title TEXT NOT NULL,
    page_number INTEGER,
    chunk_content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    -- 1536-dimensional dense vector embeddings (Compatible with OpenAI / Indic-BGE)
    embedding vector(1536),
    content_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_sessions (
    session_id VARCHAR(128) PRIMARY KEY,
    language_preference VARCHAR(16) NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_interaction_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_ephemeral_guest BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE chat_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(128) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    sender_role VARCHAR(16) NOT NULL, -- 'user', 'assistant', 'system'
    content_text TEXT NOT NULL,
    language_detected VARCHAR(16),
    citations JSONB, -- Direct URLs and guideline page numbers referenced
    evaluation_id UUID REFERENCES user_evaluations(evaluation_id) ON DELETE SET NULL,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 6. DPDP ACT 2023 COMPLIANCE & SECURITY AUDIT LOGS
-- =============================================================================

CREATE TABLE dpdp_consent_logs (
    consent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(128) NOT NULL,
    consent_purpose VARCHAR(128) NOT NULL, -- e.g. 'SCHOLARSHIP_ELIGIBILITY_EVALUATION'
    is_consent_granted BOOLEAN NOT NULL,
    client_ip_hash CHAR(64) NOT NULL, -- Anonymized salted SHA-256 hash (No raw IP stored)
    user_agent_hash CHAR(64) NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours')
);

CREATE TABLE audit_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(64) NOT NULL, -- 'SCHEME_VERSION_PUBLISHED', 'RULE_MODIFIED', 'BULK_EVAL'
    performed_by VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    action_details JSONB NOT NULL,
    prev_record_hash CHAR(64), -- Cryptographic tamper-evident hash chaining
    current_record_hash CHAR(64) NOT NULL
);

-- =============================================================================
-- INDEXES & PERFORMANCE OPTIMIZATIONS
-- =============================================================================

-- Scheme & Version lookup indexes
CREATE INDEX idx_schemes_active ON schemes(is_active);
CREATE INDEX idx_scheme_versions_lookup ON scheme_versions(scheme_id, academic_year);
CREATE INDEX idx_scheme_versions_sha ON scheme_versions(content_sha256);

-- Eligibility fast-filter GIN indexes on JSONB
CREATE INDEX idx_rules_target_categories ON scheme_eligibility_rules USING GIN(target_categories);
CREATE INDEX idx_rules_eligible_domiciles ON scheme_eligibility_rules USING GIN(eligible_domiciles);
CREATE INDEX idx_rules_eligible_courses ON scheme_eligibility_rules USING GIN(eligible_course_levels);
CREATE INDEX idx_rules_income_ceiling ON scheme_eligibility_rules(income_ceiling_annual_inr);
CREATE INDEX idx_rules_marks_percent ON scheme_eligibility_rules(minimum_qualifying_marks_percent);

-- Application window status index
CREATE INDEX idx_windows_status ON scheme_application_windows(portal_status, window_close_date);

-- HNSW Vector Index on Knowledge Chunks for Sub-50ms Approximate Nearest Neighbor Retrieval
CREATE INDEX idx_knowledge_chunks_embedding ON scheme_knowledge_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-Text Search Index on English & Multilingual Chunk Content (Sparse Search)
CREATE INDEX idx_knowledge_chunks_fts ON scheme_knowledge_chunks USING GIN(to_tsvector('english', chunk_content));

-- Evaluation performance indexes
CREATE INDEX idx_evaluations_session ON user_evaluations(session_id, evaluated_at);
CREATE INDEX idx_eval_results_eval_id ON evaluation_rule_results(evaluation_id, evaluation_status);
CREATE INDEX idx_eval_results_scheme_id ON evaluation_rule_results(scheme_id);

-- Chat history ordering index
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id, created_at ASC);

-- Consent validity index
CREATE INDEX idx_consent_validity ON dpdp_consent_logs(session_id, expires_at);
