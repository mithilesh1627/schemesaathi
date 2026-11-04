"""Initial M0 schema migration for SchemeSaathi.

Revision ID: 0001_initial_m0_schema
Revises: None
Create Date: 2026-11-04 15:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_m0_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Extensions (PostgreSQL only)
    if is_postgres:
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
        op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # 2. Enums
    scheme_level_enum = sa.Enum(
        "CENTRAL_SECTOR",
        "CENTRALLY_SPONSORED",
        "STATE_SECTOR",
        "CORPORATE_CSR_GOVT_PARTNERED",
        name="scheme_level_enum",
    )
    verification_status_enum = sa.Enum(
        "OFFICIAL_VERIFIED",
        "OFFICIAL_PROVISIONAL",
        "REQUIRES_REVALUATION",
        "DEPRECATED",
        name="verification_status_enum",
    )
    portal_type_enum = sa.Enum(
        "NSP_2_0",
        "MYSCHEME",
        "STATE_DIRECT_PORTAL",
        "OFFLINE_INSTITUTE",
        name="portal_type_enum",
    )
    portal_window_status_enum = sa.Enum(
        "OPEN",
        "CLOSED",
        "UPCOMING",
        "EXTENDED",
        "UNKNOWN",
        name="portal_window_status_enum",
    )
    evaluation_status_enum = sa.Enum(
        "ELIGIBLE_NOW",
        "ELIGIBLE_OFF_CYCLE",
        "CONDITIONALLY_ELIGIBLE",
        "INELIGIBLE",
        name="evaluation_status_enum",
    )

    json_type = postgresql.JSONB() if is_postgres else sa.JSON()
    vector_type = Vector(1536) if is_postgres else sa.JSON()

    # 3. Create 'schemes' table
    op.create_table(
        "schemes",
        sa.Column("scheme_id", sa.String(length=64), primary_key=True),
        sa.Column("official_code", sa.String(length=128), nullable=False),
        sa.Column("title_en", sa.Text(), nullable=False),
        sa.Column("title_hi", sa.Text(), nullable=True),
        sa.Column("title_mni_beng", sa.Text(), nullable=True),
        sa.Column("title_mni_latn", sa.Text(), nullable=True),
        sa.Column("issuing_level", scheme_level_enum, nullable=False),
        sa.Column("ministry_or_department", sa.String(length=255), nullable=False),
        sa.Column("implementing_agency", sa.String(length=255), nullable=False),
        sa.Column("canonical_source_url", sa.Text(), nullable=False),
        sa.Column("guidelines_document_url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_schemes_active", "schemes", ["is_active"])

    # 4. Create 'scheme_versions' table
    op.create_table(
        "scheme_versions",
        sa.Column("version_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "scheme_id",
            sa.String(length=64),
            sa.ForeignKey("schemes.scheme_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("guideline_publication_date", sa.Date(), nullable=True),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "verification_status",
            verification_status_enum,
            server_default="OFFICIAL_PROVISIONAL",
            nullable=False,
        ),
        sa.Column("verified_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("scheme_id", "version_number", name="uq_scheme_version"),
    )
    op.create_index("idx_scheme_versions_lookup", "scheme_versions", ["scheme_id", "academic_year"])
    op.create_index("idx_scheme_versions_sha", "scheme_versions", ["content_sha256"])

    # 5. Create 'scheme_eligibility_rules' table
    op.create_table(
        "scheme_eligibility_rules",
        sa.Column("rule_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("scheme_versions.version_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("income_ceiling_annual_inr", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "minimum_qualifying_marks_percent", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.Column("target_categories", json_type, nullable=False),
        sa.Column("eligible_genders", json_type, nullable=False),
        sa.Column("eligible_domiciles", json_type, nullable=False),
        sa.Column("eligible_course_levels", json_type, nullable=False),
        sa.Column(
            "mandates_aishe_institution",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "permits_distance_learning",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("ast_rule_logic", json_type, nullable=False),
        sa.Column("rule_description_en", sa.Text(), nullable=False),
        sa.Column("rule_description_mni", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("version_id", name="uq_version_rule"),
    )
    op.create_index(
        "idx_rules_income_ceiling", "scheme_eligibility_rules", ["income_ceiling_annual_inr"]
    )
    op.create_index(
        "idx_rules_marks_percent", "scheme_eligibility_rules", ["minimum_qualifying_marks_percent"]
    )

    # 6. Create 'scheme_application_windows' table
    op.create_table(
        "scheme_application_windows",
        sa.Column("window_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("scheme_versions.version_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("portal_type", portal_type_enum, nullable=False),
        sa.Column("portal_url", sa.Text(), nullable=False),
        sa.Column(
            "portal_status", portal_window_status_enum, server_default="UNKNOWN", nullable=False
        ),
        sa.Column("window_open_date", sa.Date(), nullable=True),
        sa.Column("window_close_date", sa.Date(), nullable=True),
        sa.Column("defect_verification_close_date", sa.Date(), nullable=True),
        sa.Column("institute_verification_close_date", sa.Date(), nullable=True),
        sa.Column(
            "requires_otr_face_rd", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "requires_freeship_card", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "status_last_verified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "idx_windows_status", "scheme_application_windows", ["portal_status", "window_close_date"]
    )

    # 7. Create 'scheme_benefits' table
    op.create_table(
        "scheme_benefits",
        sa.Column("benefit_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("scheme_versions.version_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "maintenance_allowance_day_scholar_annual_inr",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column(
            "maintenance_allowance_hosteller_annual_inr",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column("tuition_fee_coverage_desc", sa.Text(), nullable=False),
        sa.Column(
            "book_and_equipment_grant_annual_inr", sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column(
            "disbursement_mechanism",
            sa.String(length=128),
            server_default="DBT_PFMS",
            nullable=False,
        ),
        sa.Column("benefit_summary_en", sa.Text(), nullable=False),
        sa.Column("benefit_summary_hi", sa.Text(), nullable=True),
        sa.Column("benefit_summary_mni", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 8. Create 'scheme_mandatory_documents' table
    op.create_table(
        "scheme_mandatory_documents",
        sa.Column("doc_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("scheme_versions.version_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_code", sa.String(length=64), nullable=False),
        sa.Column("document_name_en", sa.String(length=255), nullable=False),
        sa.Column("document_name_mni", sa.String(length=255), nullable=True),
        sa.Column("issuing_authority_rule", sa.Text(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("validity_duration_months", sa.Integer(), nullable=True),
        sa.Column("critical_validation_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 9. Create 'institutes_aishe' table
    op.create_table(
        "institutes_aishe",
        sa.Column("aishe_code", sa.String(length=32), primary_key=True),
        sa.Column("institution_name", sa.Text(), nullable=False),
        sa.Column("institution_type", sa.String(length=64), nullable=False),
        sa.Column("state_code", sa.String(length=32), nullable=False),
        sa.Column("district_name", sa.String(length=128), nullable=False),
        sa.Column("is_active_on_nsp", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "last_verified_academic_year",
            sa.String(length=32),
            server_default="2024-2025",
            nullable=False,
        ),
    )

    # 10. Create 'user_evaluations' table
    op.create_table(
        "user_evaluations",
        sa.Column("evaluation_id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column(
            "evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("category_evaluated", sa.String(length=32), nullable=False),
        sa.Column("income_evaluated", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("domicile_evaluated", sa.String(length=64), nullable=False),
        sa.Column("course_level_evaluated", sa.String(length=64), nullable=False),
        sa.Column("marks_percent_evaluated", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("gender_evaluated", sa.String(length=16), nullable=True),
        sa.Column(
            "is_disability_evaluated", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_displaced_affected", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("total_schemes_checked", sa.Integer(), nullable=False),
        sa.Column("total_eligible", sa.Integer(), nullable=False),
        sa.Column("evaluation_duration_ms", sa.Integer(), nullable=False),
    )
    op.create_index("idx_evaluations_session", "user_evaluations", ["session_id", "evaluated_at"])

    # 11. Create 'evaluation_rule_results' table
    op.create_table(
        "evaluation_rule_results",
        sa.Column("result_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey("user_evaluations.evaluation_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scheme_id",
            sa.String(length=64),
            sa.ForeignKey("schemes.scheme_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("scheme_versions.version_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evaluation_status", evaluation_status_enum, nullable=False),
        sa.Column("passed_income_check", sa.Boolean(), nullable=False),
        sa.Column("passed_category_check", sa.Boolean(), nullable=False),
        sa.Column("passed_domicile_check", sa.Boolean(), nullable=False),
        sa.Column("passed_marks_check", sa.Boolean(), nullable=False),
        sa.Column("passed_course_check", sa.Boolean(), nullable=False),
        sa.Column("missing_criteria_fields", json_type, nullable=True),
        sa.Column("ineligibility_reasons", json_type, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "idx_eval_results_eval_id",
        "evaluation_rule_results",
        ["evaluation_id", "evaluation_status"],
    )
    op.create_index("idx_eval_results_scheme_id", "evaluation_rule_results", ["scheme_id"])

    # 12. Create 'scheme_knowledge_chunks' table
    op.create_table(
        "scheme_knowledge_chunks",
        sa.Column("chunk_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("scheme_versions.version_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scheme_id",
            sa.String(length=64),
            sa.ForeignKey("schemes.scheme_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language_code", sa.String(length=16), server_default="en", nullable=False),
        sa.Column("section_title", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", vector_type, nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # 13. Create 'chat_sessions' table
    op.create_table(
        "chat_sessions",
        sa.Column("session_id", sa.String(length=128), primary_key=True),
        sa.Column("language_preference", sa.String(length=16), server_default="en", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_interaction_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_ephemeral_guest", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )

    # 14. Create 'chat_messages' table
    op.create_table(
        "chat_messages",
        sa.Column("message_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=128),
            sa.ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_role", sa.String(length=16), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("language_detected", sa.String(length=16), nullable=True),
        sa.Column("citations", json_type, nullable=True),
        sa.Column(
            "evaluation_id",
            sa.Uuid(),
            sa.ForeignKey("user_evaluations.evaluation_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_chat_messages_session", "chat_messages", ["session_id", "created_at"])

    # 15. Create 'dpdp_consent_logs' table
    op.create_table(
        "dpdp_consent_logs",
        sa.Column("consent_id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("consent_purpose", sa.String(length=128), nullable=False),
        sa.Column("is_consent_granted", sa.Boolean(), nullable=False),
        sa.Column("client_ip_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_consent_validity", "dpdp_consent_logs", ["session_id", "expires_at"])

    # 16. Create 'audit_events' table
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("performed_by", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("action_details", json_type, nullable=False),
        sa.Column("prev_record_hash", sa.String(length=64), nullable=True),
        sa.Column("current_record_hash", sa.String(length=64), nullable=False),
    )

    # 17. Specialized PostgreSQL Indexes (GIN & HNSW)
    if is_postgres:
        op.execute(
            "CREATE INDEX idx_rules_target_categories ON scheme_eligibility_rules USING GIN(target_categories)"
        )
        op.execute(
            "CREATE INDEX idx_rules_eligible_domiciles ON scheme_eligibility_rules USING GIN(eligible_domiciles)"
        )
        op.execute(
            "CREATE INDEX idx_rules_eligible_courses ON scheme_eligibility_rules USING GIN(eligible_course_levels)"
        )
        op.execute(
            "CREATE INDEX idx_knowledge_chunks_embedding ON scheme_knowledge_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )
        op.execute(
            "CREATE INDEX idx_knowledge_chunks_fts ON scheme_knowledge_chunks USING GIN(to_tsvector('english', chunk_content))"
        )


def downgrade() -> None:
    # Drop tables in reverse topological order
    op.drop_table("audit_events")
    op.drop_table("dpdp_consent_logs")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("scheme_knowledge_chunks")
    op.drop_table("evaluation_rule_results")
    op.drop_table("user_evaluations")
    op.drop_table("institutes_aishe")
    op.drop_table("scheme_mandatory_documents")
    op.drop_table("scheme_benefits")
    op.drop_table("scheme_application_windows")
    op.drop_table("scheme_eligibility_rules")
    op.drop_table("scheme_versions")
    op.drop_table("schemes")

    # Drop custom enum types (PostgreSQL only)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS evaluation_status_enum")
        op.execute("DROP TYPE IF EXISTS portal_window_status_enum")
        op.execute("DROP TYPE IF EXISTS portal_type_enum")
        op.execute("DROP TYPE IF EXISTS verification_status_enum")
        op.execute("DROP TYPE IF EXISTS scheme_level_enum")
