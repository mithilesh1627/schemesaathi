"""In-Memory and Redis-Compatible Session Repository with Automatic TTL Expiration."""

import asyncio

from src.core.logging import get_logger
from src.modules.chat.domain.models import SESSION_TTL_SECONDS, ChatSession

logger = get_logger(__name__)


class ChatSessionRepository:
    """Stores and retrieves active chat sessions with automatic TTL expiration."""

    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, session_id: str) -> ChatSession | None:
        """Retrieve active session by ID. Returns None if not found or expired."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired(self._ttl_seconds):
                logger.info(
                    "Session %s has expired (TTL=%ds). Pruning.", session_id, self._ttl_seconds
                )
                del self._sessions[session_id]
                return None
            return session

    async def save(self, session: ChatSession) -> None:
        """Persist or update session in store."""
        async with self._lock:
            self._sessions[session.session_id] = session

    async def delete(self, session_id: str) -> bool:
        """Remove session from store."""
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None

    async def clear(self) -> None:
        """Clear all active sessions (used in test teardown)."""
        async with self._lock:
            self._sessions.clear()


# Global singleton instance
_session_repo = ChatSessionRepository()


def get_session_repository() -> ChatSessionRepository:
    """Return singleton session repository instance."""
    return _session_repo
