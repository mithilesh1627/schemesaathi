"""Domain Exceptions for Chat, Synchronizer, and Citation Subsystems."""

from typing import Any

from src.core.errors import SchemeSaathiError


class ChatError(SchemeSaathiError):
    """Base exception for chat and conversational reasoning errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_CHAT_GENERAL",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class SessionNotFoundError(ChatError):
    """Raised when the specified session ID does not exist or has expired."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Chat session '{session_id}' was not found or has expired.",
            error_code="ERR_SESSION_NOT_FOUND",
            status_code=404,
            details={"session_id": session_id},
        )


class CitationCheckError(ChatError):
    """Raised when citation validation fails during answer post-processing."""

    def __init__(self, message: str, ungrounded_claims: list[str] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="ERR_CITATION_CHECK_FAILED",
            status_code=422,
            details={"ungrounded_claims": ungrounded_claims or []},
        )


class SynchronizerError(ChatError):
    """Raised when deterministic synchronizer encounters inconsistent profile state."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            error_code="ERR_SYNCHRONIZER_CONFLICT",
            status_code=400,
        )
