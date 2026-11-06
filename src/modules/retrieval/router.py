"""FastAPI Router for Public Hybrid Retrieval Search API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.retrieval.application.retrieval_service import RetrievalService
from src.modules.retrieval.application.schemas import (
    ApplicationWindowInfo,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievedChunkResponse,
)

router = APIRouter(prefix="/retrieval", tags=["Hybrid Retrieval"])


@router.post(
    "/search",
    response_model=RetrievalSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Public Hybrid Search over Official Statutory Guidelines",
    description=(
        "Hybrid sparse (BM25 / PostgreSQL tsvector) + dense (pgvector HNSW) retrieval "
        "merged via Reciprocal Rank Fusion (k=60). Includes Unicode script routing "
        "(Latin, Bengali, Meetei Mayek) and domain acronym expansion. Returns chunks and provenance only."
    ),
)
async def search_guidelines(
    request: RetrievalSearchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RetrievalSearchResponse:
    """Execute deterministic hybrid retrieval over official statutory knowledge chunks."""
    service = RetrievalService(session)
    search_res = await service.search(
        query=request.query,
        top_k=request.top_k,
        state_filter=request.state_filter,
    )

    formatted_results = [
        RetrievedChunkResponse(
            chunk_id=c.chunk_id,
            scheme_id=c.scheme_id,
            version_id=c.version_id,
            section_title=c.section_title,
            chunk_content=c.chunk_content,
            token_count=c.token_count,
            page_number=c.page_number,
            source_url=c.source_url,
            document_sha256=c.document_sha256,
            academic_year=c.academic_year,
            application_window=ApplicationWindowInfo(
                window_open_date=c.window_open_date,
                window_close_date=c.window_close_date,
                portal_status=c.portal_status,
                is_window_closed=c.is_window_closed,
            ),
            sparse_rank=c.sparse_rank,
            dense_rank=c.dense_rank,
            rrf_score=round(c.rrf_score, 6),
        )
        for c in search_res["results"]
    ]

    return RetrievalSearchResponse(
        query=search_res["query"],
        detected_script=search_res["detected_script"],
        expanded_query=search_res["expanded_query"],
        transliteration_applied=search_res.get("transliteration_applied", False),
        expanded_acronyms=search_res.get("expanded_acronyms", []),
        total_results=len(formatted_results),
        results=formatted_results,
        invented_chunk_count=0,
        disclaimer=search_res["disclaimer"],
    )
