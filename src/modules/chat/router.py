"""FastAPI Router for Grounded Conversational API."""

import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.dependencies import enforce_chat_rate_limit
from src.modules.catalog.infrastructure.repositories import SchemeRepository
from src.modules.chat.application.auditor import DocumentReadinessAuditor
from src.modules.chat.application.chat_service import ChatService
from src.modules.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    SchemeChecklistDocumentItem,
    SchemeChecklistResponse,
)
from src.modules.chat.domain.exceptions import SessionNotFoundError
from src.modules.chat.infrastructure.session_repository import get_session_repository
from src.modules.retrieval.infrastructure.repositories import RetrievalRepository

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


@router.get(
    "/checklist",
    response_model=list[SchemeChecklistResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Statutory Document Readiness Checklists",
    description=(
        "Returns chunk-derived document checklists for all active schemes using DocumentReadinessAuditor."
    ),
)
async def get_all_scheme_checklists(
    db_session: AsyncSession = Depends(get_db_session),
) -> list[SchemeChecklistResponse]:
    """Exposes Sprint 4 DocumentReadinessAuditor dynamically derived checklists for all seeded schemes."""
    scheme_repo = SchemeRepository(db_session)
    retrieval_repo = RetrievalRepository(db_session)

    schemes, _ = await scheme_repo.list_schemes(limit=50)
    chunks = await retrieval_repo.get_all_chunks()
    chunk_dicts = [{"scheme_id": c.scheme_id, "chunk_content": c.chunk_content} for c in chunks]

    responses: list[SchemeChecklistResponse] = []
    for s in sorted(schemes, key=lambda x: x.scheme_id):
        full_scheme = await scheme_repo.get_by_id(s.scheme_id)
        latest_version = full_scheme.versions[0] if full_scheme and full_scheme.versions else None
        window = latest_version.application_window if latest_version else None

        close_date = (
            str(window.window_close_date) if window and window.window_close_date else "2025-11-30"
        )
        ay = latest_version.academic_year if latest_version else "2025-2026"
        p_status = window.portal_status.value if window and window.portal_status else "CLOSED"
        portal_url = (
            window.portal_url
            if window and window.portal_url
            else (s.guidelines_document_url or s.canonical_source_url)
        )

        doc_names = DocumentReadinessAuditor.derive_required_documents_from_chunks(
            chunk_dicts, scheme_id=s.scheme_id
        )

        if doc_names:
            doc_items = [
                SchemeChecklistDocumentItem(
                    id=re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"),
                    name=name,
                    desc="Statutory document derived from official guideline chunks.",
                    status="UNKNOWN",
                    is_available=True,
                )
                for name in doc_names
            ]
            responses.append(
                SchemeChecklistResponse(
                    scheme_id=s.scheme_id,
                    title=s.title_en,
                    academic_year=ay,
                    window_close_date=close_date,
                    portal_status=p_status,
                    portal_url=portal_url,
                    documents=doc_items,
                    has_guideline_documents=True,
                    guidance_note=None,
                )
            )
        else:
            # Guideline has no chunk-derived document requirements -> render UNKNOWN with explicit note
            doc_items = [
                SchemeChecklistDocumentItem(
                    id="guideline_docs_unavailable",
                    name="Guideline Documents Checklist",
                    desc="Document list not available from the guideline.",
                    status="UNKNOWN",
                    is_available=False,
                )
            ]
            responses.append(
                SchemeChecklistResponse(
                    scheme_id=s.scheme_id,
                    title=s.title_en,
                    academic_year=ay,
                    window_close_date=close_date,
                    portal_status=p_status,
                    portal_url=portal_url,
                    documents=doc_items,
                    has_guideline_documents=False,
                    guidance_note="Document list not available from the guideline.",
                )
            )

    return responses


@router.get(
    "/checklist/{scheme_id}",
    response_model=SchemeChecklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Statutory Document Readiness Checklist for Scheme",
)
async def get_scheme_checklist(
    scheme_id: str,
    db_session: AsyncSession = Depends(get_db_session),
) -> SchemeChecklistResponse:
    """Fetch checklist for a specific scheme."""
    checklists = await get_all_scheme_checklists(db_session=db_session)
    for c in checklists:
        if c.scheme_id == scheme_id:
            return c
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Scheme '{scheme_id}' not found in active catalog.",
    )
