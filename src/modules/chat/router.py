"""FastAPI Router for Grounded Conversational API."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.dependencies import enforce_chat_rate_limit
from src.modules.chat.application.chat_service import ChatService
from src.modules.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
)
from src.modules.chat.domain.exceptions import SessionNotFoundError
from src.modules.chat.infrastructure.session_repository import get_session_repository

router = APIRouter(prefix="/chat", tags=["Grounded Conversational Chat"])


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_chat_rate_limit)],
    summary="Send Message to Grounded Conversational Assistant",
    description=(
        "Processes user query through script routing, hybrid retrieval, deterministic eligibility "
        "state synchronization, and citation-checked grounded generation. Strictly enforces "
        "inline citations [^n] and refuses ungrounded claims."
    ),
)
async def send_chat_message(
    request: ChatMessageRequest,
    db_session: AsyncSession = Depends(get_db_session),
) -> ChatMessageResponse:
    """Execute grounded conversational turn with state synchronization and citation verification."""
    service = ChatService(db_session=db_session)
    return await service.process_turn(request)


@router.post(
    "/message/stream",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_chat_rate_limit)],
    summary="Stream Grounded Conversational Turn (Server-Sent Events)",
    description="Streams tokens and structured citation metadata over an SSE event stream.",
)
async def stream_chat_message(
    request: ChatMessageRequest,
    db_session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Stream grounded answer using Server-Sent Events (SSE)."""
    service = ChatService(db_session=db_session)
    resp = await service.process_turn(request)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Event 1: Routing & Retrieval metadata
        meta = {
            "session_id": resp.session_id,
            "detected_language": resp.detected_language,
            "routed_query": resp.routed_query,
            "chunks_retrieved_count": resp.chunks_retrieved_count,
            "invented_chunk_count": resp.invented_chunk_count,
        }
        yield f"event: metadata\ndata: {json.dumps(meta)}\n\n"

        # Event 2: Token chunks simulation over grounded answer
        words = resp.answer.split(" ")
        for i in range(0, len(words), 3):
            token_chunk = " ".join(words[i : i + 3]) + " "
            yield f"event: token\ndata: {json.dumps({'text': token_chunk})}\n\n"

        # Event 3: Final verified citations and audit payload
        final_payload = {
            "citations": [c.model_dump() for c in resp.citations],
            "eligibility_results": [r.model_dump() for r in (resp.eligibility_results or [])],
            "document_audit": resp.document_audit.model_dump() if resp.document_audit else None,
            "is_refusal": resp.is_refusal,
        }
        yield f"event: complete\ndata: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Initialize New Chat Session",
)
async def create_chat_session(
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a new bounded, expiring conversational session."""
    service = ChatService(db_session=db_session)
    session = await service.get_or_create_session(session_id="")
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "status": "active",
    }


@router.get(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve Session State and Bounded History",
)
async def get_session_info(
    session_id: str,
    _db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch session state, profile facts, and history with PII redaction."""
    repo = get_session_repository()
    session = await repo.get(session_id)
    if session is None:
        raise SessionNotFoundError(session_id=session_id)

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "profile_facts": session.profile_facts.__dict__,
        "history": [
            {
                "role": m.role.value,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "citations_count": len(m.citations),
            }
            for m in session.history
        ],
        "is_expired": session.is_expired(),
    }
