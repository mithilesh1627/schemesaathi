"""Declarative SQLAlchemy 2 Models for SchemeSaathi Schema."""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from src.modules.catalog.domain.enums import (
    DocumentLifecycleState,
    EvaluationStatus,
    PortalType,
    PortalWindowStatus,
    SchemeLevel,
    VerificationStatus,
)


class Base(DeclarativeBase):
    """Base declarative class for all SchemeSaathi models."""

    pass


# Dialect-agnostic JSON type that uses JSONB on PostgreSQL and JSON on SQLite
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class FlexibleVector(TypeDecorator[Any]):
    """Vector type that gracefully falls back to JSON on SQLite for testing."""

    impl = Vector
    cache_ok = True

    def __init__(self, dim: int = 1536, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(Vector(self.dim))


def utc_now() -> datetime:
    """Return current timestamp with UTC timezone."""
    return datetime.now(UTC)


class Scheme(Base):
    """Core master scheme record."""

    __tablename__ = "schemes"

    scheme_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    official_code: Mapped[str] = mapped_column(String(128), nullable=False)
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_mni_beng: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_mni_latn: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuing_level: Mapped[SchemeLevel] = mapped_column(
        Enum(SchemeLevel, name="scheme_level_enum"), nullable=False
    )
    ministry_or_department: Mapped[str] = mapped_column(String(255), nullable=False)
    implementing_agency: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_source_url: Mapped[str] = mapped_column(Text, nullable=False)
    guidelines_document_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    versions: Mapped[list["SchemeVersion"]] = relationship(
        "SchemeVersion", back_populates="scheme", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_schemes_active", "is_active"),)


class SchemeVersion(Base):
    """Academic session specific guideline version with cryptographic hash."""

    __tablename__ = "scheme_versions"

    version_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scheme_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("schemes.scheme_id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. '2024-2025'
    guideline_publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(
        String(32), default=DocumentLifecycleState.STORED.value, nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status_enum"),
        default=VerificationStatus.OFFICIAL_PROVISIONAL,
        nullable=False,
    )
    verified_by_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="versions")
    eligibility_rule: Mapped["SchemeEligibilityRule | None"] = relationship(
        "SchemeEligibilityRule",
        back_populates="version",
        uselist=False,
        cascade="all, delete-orphan",
    )
    application_window: Mapped["SchemeApplicationWindow | None"] = relationship(
        "SchemeApplicationWindow",
        back_populates="version",
        uselist=False,
        cascade="all, delete-orphan",
    )
    benefit: Mapped["SchemeBenefit | None"] = relationship(
        "SchemeBenefit", back_populates="version", uselist=False, cascade="all, delete-orphan"
    )
    mandatory_documents: Mapped[list["SchemeMandatoryDocument"]] = relationship(
        "SchemeMandatoryDocument", back_populates="version", cascade="all, delete-orphan"
    )
    knowledge_chunks: Mapped[list["SchemeKnowledgeChunk"]] = relationship(
        "SchemeKnowledgeChunk", back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("scheme_id", "version_number", name="uq_scheme_version"),
        Index("idx_scheme_versions_lookup", "scheme_id", "academic_year"),
        Index("idx_scheme_versions_sha", "content_sha256"),
    )


class SchemeEligibilityRule(Base):
    """Deterministic eligibility criteria stored in JSON-Logic AST."""

    __tablename__ = "scheme_eligibility_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.version_id", ondelete="CASCADE"), nullable=False
    )
    income_ceiling_annual_inr: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    minimum_qualifying_marks_percent: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    target_categories: Mapped[Any] = mapped_column(JSON_TYPE, default=list, nullable=False)
    eligible_genders: Mapped[Any] = mapped_column(
        JSON_TYPE, default=lambda: ["ANY"], nullable=False
    )
    eligible_domiciles: Mapped[Any] = mapped_column(
        JSON_TYPE, default=lambda: ["ALL_INDIA"], nullable=False
    )
    eligible_course_levels: Mapped[Any] = mapped_column(JSON_TYPE, nullable=False)
    mandates_aishe_institution: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    permits_distance_learning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ast_rule_logic: Mapped[Any] = mapped_column(JSON_TYPE, nullable=False)
    rule_description_en: Mapped[str] = mapped_column(Text, nullable=False)
    rule_description_mni: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    version: Mapped["SchemeVersion"] = relationship(
        "SchemeVersion", back_populates="eligibility_rule"
    )

    __table_args__ = (
        UniqueConstraint("version_id", name="uq_version_rule"),
        Index("idx_rules_income_ceiling", "income_ceiling_annual_inr"),
        Index("idx_rules_marks_percent", "minimum_qualifying_marks_percent"),
    )


class SchemeApplicationWindow(Base):
    """Application portal timeline and lifecycle status."""

    __tablename__ = "scheme_application_windows"

    window_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.version_id", ondelete="CASCADE"), nullable=False
    )
    portal_type: Mapped[PortalType] = mapped_column(
        Enum(PortalType, name="portal_type_enum"), nullable=False
    )
    portal_url: Mapped[str] = mapped_column(Text, nullable=False)
    portal_status: Mapped[PortalWindowStatus] = mapped_column(
        Enum(PortalWindowStatus, name="portal_window_status_enum"),
        default=PortalWindowStatus.UNKNOWN,
        nullable=False,
    )
    window_open_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    defect_verification_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    institute_verification_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    requires_otr_face_rd: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_freeship_card: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    version: Mapped["SchemeVersion"] = relationship(
        "SchemeVersion", back_populates="application_window"
    )

    __table_args__ = (Index("idx_windows_status", "portal_status", "window_close_date"),)


class SchemeBenefit(Base):
    """Financial and academic assistance benefits."""

    __tablename__ = "scheme_benefits"

    benefit_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.version_id", ondelete="CASCADE"), nullable=False
    )
    maintenance_allowance_day_scholar_annual_inr: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    maintenance_allowance_hosteller_annual_inr: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    tuition_fee_coverage_desc: Mapped[str] = mapped_column(Text, nullable=False)
    book_and_equipment_grant_annual_inr: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    disbursement_mechanism: Mapped[str] = mapped_column(
        String(128), default="DBT_PFMS", nullable=False
    )
    benefit_summary_en: Mapped[str] = mapped_column(Text, nullable=False)
    benefit_summary_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefit_summary_mni: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    version: Mapped["SchemeVersion"] = relationship("SchemeVersion", back_populates="benefit")


class SchemeMandatoryDocument(Base):
    """Document checklist requirements and issuing authority rules."""

    __tablename__ = "scheme_mandatory_documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.version_id", ondelete="CASCADE"), nullable=False
    )
    document_code: Mapped[str] = mapped_column(String(64), nullable=False)
    document_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    document_name_mni: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issuing_authority_rule: Mapped[str] = mapped_column(Text, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validity_duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    version: Mapped["SchemeVersion"] = relationship(
        "SchemeVersion", back_populates="mandatory_documents"
    )


class InstitutesAishe(Base):
    """Institutional AISHE and U-DISE directory lookup."""

    __tablename__ = "institutes_aishe"

    aishe_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    institution_name: Mapped[str] = mapped_column(Text, nullable=False)
    institution_type: Mapped[str] = mapped_column(String(64), nullable=False)
    state_code: Mapped[str] = mapped_column(String(32), nullable=False)
    district_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active_on_nsp: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_verified_academic_year: Mapped[str] = mapped_column(
        String(32), default="2024-2025", nullable=False
    )


class UserEvaluation(Base):
    """Ephemeral evaluation record."""

    __tablename__ = "user_evaluations"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    category_evaluated: Mapped[str] = mapped_column(String(32), nullable=False)
    income_evaluated: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    domicile_evaluated: Mapped[str] = mapped_column(String(64), nullable=False)
    course_level_evaluated: Mapped[str] = mapped_column(String(64), nullable=False)
    marks_percent_evaluated: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    gender_evaluated: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_disability_evaluated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_displaced_affected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_schemes_checked: Mapped[int] = mapped_column(Integer, nullable=False)
    total_eligible: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    results: Mapped[list["EvaluationRuleResult"]] = relationship(
        "EvaluationRuleResult", back_populates="evaluation", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_evaluations_session", "session_id", "evaluated_at"),)


class EvaluationRuleResult(Base):
    """Detailed scheme evaluation outcome with diagnostics."""

    __tablename__ = "evaluation_rule_results"

    result_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_evaluations.evaluation_id", ondelete="CASCADE"), nullable=False
    )
    scheme_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("schemes.scheme_id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.version_id", ondelete="CASCADE"), nullable=False
    )
    evaluation_status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus, name="evaluation_status_enum"), nullable=False
    )
    passed_income_check: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed_category_check: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed_domicile_check: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed_marks_check: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed_course_check: Mapped[bool] = mapped_column(Boolean, nullable=False)
    missing_criteria_fields: Mapped[Any | None] = mapped_column(JSON_TYPE, nullable=True)
    ineligibility_reasons: Mapped[Any | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    evaluation: Mapped["UserEvaluation"] = relationship("UserEvaluation", back_populates="results")

    __table_args__ = (
        Index("idx_eval_results_eval_id", "evaluation_id", "evaluation_status"),
        Index("idx_eval_results_scheme_id", "scheme_id"),
    )


class SchemeKnowledgeChunk(Base):
    """Chunked knowledge from official guidelines with vector embeddings."""

    __tablename__ = "scheme_knowledge_chunks"

    chunk_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_versions.version_id", ondelete="CASCADE"), nullable=False
    )
    scheme_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("schemes.scheme_id", ondelete="CASCADE"), nullable=False
    )
    language_code: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    section_title: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(FlexibleVector(1024), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(64), default="BAAI/bge-m3", nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    version: Mapped["SchemeVersion"] = relationship(
        "SchemeVersion", back_populates="knowledge_chunks"
    )


class ChatSession(Base):
    """Conversational session metadata."""

    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    language_preference: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    is_ephemeral_guest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """Individual conversational chat turn with inline citations."""

    __tablename__ = "chat_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    sender_role: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # 'user', 'assistant', 'system'
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    language_detected: Mapped[str | None] = mapped_column(String(16), nullable=True)
    citations: Mapped[Any | None] = mapped_column(JSON_TYPE, nullable=True)
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_evaluations.evaluation_id", ondelete="SET NULL"), nullable=True
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    __table_args__ = (Index("idx_chat_messages_session", "session_id", "created_at"),)


class DpdpConsentLog(Base):
    """Consent records under DPDP Act 2023 with salted IP hashing."""

    __tablename__ = "dpdp_consent_logs"

    consent_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    consent_purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    is_consent_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    client_ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("idx_consent_validity", "session_id", "expires_at"),)


class AuditEvent(Base):
    """Cryptographically chained tamper-evident audit log."""

    __tablename__ = "audit_events"

    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action_details: Mapped[Any] = mapped_column(JSON_TYPE, nullable=False)
    prev_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
