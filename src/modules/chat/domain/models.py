"""Domain Models for Grounded Conversational Sessions, Citations, and Document Readiness."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.core.security import redact_pii_text
from src.modules.chat.domain.enums import AuditStatus, ChatRole

# Explicit boundaries for session storage and context bounds
SESSION_TTL_SECONDS = 3600  # Sessions expire after 1 hour of inactivity
MAX_SESSION_HISTORY_TURNS = 10  # Context window bound: last 10 conversation turns (20 messages)


@dataclass
class UserProfileFacts:
    """Structured user profile facts held in session state.

    The LLM never rewrites these facts. They are machine-readable and outrank
    any unstructured claims in conversation history.
    """

    domicile_state: str | None = None
    social_category: str | None = None
    annual_family_income_inr: float | None = None
    marks_percent: float | None = None
    course_level: str | None = None
    gender: str | None = None
    is_displaced: bool | None = None

    def to_evaluation_context(self) -> dict[str, Any]:
        """Convert known profile facts into deterministic AST evaluation context."""
        ctx: dict[str, Any] = {}
        if self.domicile_state:
            ctx["domicile_state"] = self.domicile_state.upper()
        if self.social_category:
            ctx["social_category"] = self.social_category.upper()
        if self.annual_family_income_inr is not None:
            ctx["annual_family_income_inr"] = float(self.annual_family_income_inr)
        if self.marks_percent is not None:
            ctx["marks_percent"] = float(self.marks_percent)
        if self.course_level:
            ctx["course_level"] = self.course_level.upper()
        if self.gender:
            ctx["gender"] = self.gender.upper()
        if self.is_displaced is not None:
            ctx["is_displaced"] = bool(self.is_displaced)
        return ctx

    def update_from_dict(self, updates: dict[str, Any]) -> list[str]:
        """Apply updates and return names of updated fields."""
        changed: list[str] = []
        for key, val in updates.items():
            if not hasattr(self, key):
                continue
            if val is None:
                continue

            current_val = getattr(self, key)
            if key == "annual_family_income_inr" or key == "marks_percent":
                try:
                    num_val = float(val)
                    if current_val != num_val:
                        setattr(self, key, num_val)
                        changed.append(key)
                except (ValueError, TypeError):
                    pass
            elif key == "is_displaced":
                bool_val = bool(val)
                if current_val != bool_val:
                    setattr(self, key, bool_val)
                    changed.append(key)
            elif isinstance(val, str):
                str_val = redact_pii_text(val).strip()
                if current_val != str_val:
                    setattr(self, key, str_val)
                    changed.append(key)
        return changed


@dataclass
class Citation:
    """A verifiable inline citation pointing to a retrieved knowledge chunk."""

    citation_number: int
    chunk_id: str
    scheme_id: str
    section: str
    source_url: str
    content_sha256: str
    academic_year: str
    window_close_date: str | None = None
    portal_status: str | None = None


@dataclass
class ChatMessage:
    """A single turn message in a session's conversation history."""

    role: ChatRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    citations: list[Citation] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Enforce unconditional 12-digit Aadhaar redaction
        self.content = redact_pii_text(self.content)


@dataclass
class AuditedDocument:
    """Status and guidance for an individual document required by a scheme."""

    document_name: str
    status: AuditStatus
    reason_or_guidance: str


@dataclass
class DocumentAuditReport:
    """Document readiness checklist and user-side warnings derived from guideline text."""

    scheme_id: str
    scheme_title: str
    documents: list[AuditedDocument]
    summary_text: str
    npci_apb_warning: str
    otr_face_rd_warning: str


@dataclass
class ChatSession:
    """Bounded, expiring conversation session containing structured state."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    profile_facts: UserProfileFacts = field(default_factory=UserProfileFacts)
    history: list[ChatMessage] = field(default_factory=list)
    last_retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    last_eligibility_results: list[dict[str, Any]] | None = None

    def add_user_message(self, text: str) -> ChatMessage:
        """Add user message with unconditional PII redaction and bounded history pruning."""
        msg = ChatMessage(role=ChatRole.USER, content=text)
        self.history.append(msg)
        self._prune_history()
        self.updated_at = datetime.now(UTC)
        return msg

    def add_assistant_message(self, text: str, citations: list[Citation]) -> ChatMessage:
        """Add assistant grounded response with verified citations and bounded history pruning."""
        msg = ChatMessage(role=ChatRole.ASSISTANT, content=text, citations=citations)
        self.history.append(msg)
        self._prune_history()
        self.updated_at = datetime.now(UTC)
        return msg

    def _prune_history(self) -> None:
        """Bound history to MAX_SESSION_HISTORY_TURNS (each turn is user + assistant)."""
        max_messages = MAX_SESSION_HISTORY_TURNS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def is_expired(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> bool:
        """Check if session exceeded time-to-live expiration."""
        elapsed = (datetime.now(UTC) - self.updated_at).total_seconds()
        return elapsed > ttl_seconds
