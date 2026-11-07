"""Chat Domain Package."""

from src.modules.chat.domain.enums import AuditStatus, ChatRole, LanguageScript
from src.modules.chat.domain.exceptions import (
    ChatError,
    CitationCheckError,
    SessionNotFoundError,
    SynchronizerError,
)
from src.modules.chat.domain.models import (
    MAX_SESSION_HISTORY_TURNS,
    SESSION_TTL_SECONDS,
    AuditedDocument,
    ChatMessage,
    ChatSession,
    Citation,
    DocumentAuditReport,
    UserProfileFacts,
)

__all__ = [
    "AuditStatus",
    "AuditedDocument",
    "ChatMessage",
    "ChatError",
    "ChatRole",
    "ChatSession",
    "Citation",
    "CitationCheckError",
    "DocumentAuditReport",
    "LanguageScript",
    "MAX_SESSION_HISTORY_TURNS",
    "SESSION_TTL_SECONDS",
    "SessionNotFoundError",
    "SynchronizerError",
    "UserProfileFacts",
]
