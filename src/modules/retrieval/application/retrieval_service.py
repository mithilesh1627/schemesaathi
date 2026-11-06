"""Hybrid Retrieval Service combining Sparse BM25/tsvector and Dense pgvector HNSW via RRF."""

import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.storage import get_storage_backend
from src.modules.catalog.domain.models import SchemeVersion
from src.modules.retrieval.application.corpus_seed_service import _EXTRACTION_CACHE
from src.modules.retrieval.application.embedding_service import local_embedder
from src.modules.retrieval.domain.acronyms import expand_query_acronyms
from src.modules.retrieval.domain.models import RetrievalCandidate
from src.modules.retrieval.domain.script_router import ScriptRouter
from src.modules.retrieval.infrastructure.extractors import (
    DigitalPdfExtractor,
    ScannedPdfOcrExtractor,
)
from src.modules.retrieval.infrastructure.repositories import RetrievalRepository

logger = get_logger(__name__)

RRF_K = 60  # Reciprocal Rank Fusion smoothing constant as specified in M0 architecture
STATUTORY_DISCLAIMER = (
    "Search results reflect retrieved statutory guidelines only. "
    "Application windows for academic year 2024-2025 are closed."
)


async def compute_invented_chunk_count(
    session: AsyncSession,
    candidates: list[RetrievalCandidate],
) -> int:
    """Dynamically verify candidate chunks against extracted text of statutory source documents."""
    if not candidates:
        return 0

    storage = get_storage_backend()
    doc_text_cache: dict[uuid.UUID, str] = {}
    invented_count = 0

    for candidate in candidates:
        v_id = candidate.version_id
        if v_id not in doc_text_cache:
            v_res = await session.execute(
                select(SchemeVersion).where(SchemeVersion.version_id == v_id)
            )
            v = v_res.scalars().first()
            if not v:
                doc_text_cache[v_id] = ""
            elif v.content_sha256 and v.content_sha256 in _EXTRACTION_CACHE:
                doc_text_cache[v_id] = _EXTRACTION_CACHE[v.content_sha256].raw_text.lower()
            elif not v.storage_path:
                doc_text_cache[v_id] = ""
            else:
                try:
                    if await storage.exists(v.storage_path):
                        pdf_bytes = await storage.retrieve(v.storage_path)
                    else:
                        static_p = Path("data/storage") / v.storage_path
                        pdf_bytes = static_p.read_bytes() if static_p.exists() else b""
                    if pdf_bytes:
                        doc_res = DigitalPdfExtractor.extract(
                            pdf_bytes, "doc.pdf", candidate.source_url
                        )
                        if doc_res.character_count < 100:
                            ocr_ext = ScannedPdfOcrExtractor()
                            if ocr_ext.is_available():
                                doc_res = ocr_ext.extract(
                                    pdf_bytes, "doc.pdf", candidate.source_url
                                )
                        doc_text_cache[v_id] = doc_res.raw_text.lower()
                    else:
                        doc_text_cache[v_id] = ""
                except Exception:
                    doc_text_cache[v_id] = ""

        raw_doc_text = doc_text_cache.get(v_id, "")
        if not raw_doc_text:
            invented_count += 1
            continue

        body = re.sub(r"^\[Scheme:[^\]]+\]\s*", "", candidate.chunk_content).strip()
        meaningful_tokens = [w.lower() for w in re.findall(r"\w+", body) if len(w) > 3]
        if not meaningful_tokens:
            meaningful_tokens = [w.lower() for w in re.findall(r"\w+", body)]

        if not meaningful_tokens:
            invented_count += 1
            continue

        matching_tokens = sum(1 for tok in meaningful_tokens if tok in raw_doc_text)
        match_rate = matching_tokens / len(meaningful_tokens)

        # A chunk is authentic if at least 70% of its meaningful terms originate from the statutory source document
        if match_rate < 0.70:
            invented_count += 1

    return invented_count


class RetrievalService:
    """Orchestrates query transliteration, acronym expansion, hybrid search, and RRF fusion."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RetrievalRepository(session)
        self.router = ScriptRouter()

    async def search(
        self,
        query: str,
        top_k: int = 20,
        state_filter: str | None = None,
    ) -> dict[str, Any]:
        """Perform deterministic hybrid search returning ranked chunks with provenance."""
        raw_query = query.strip()
        if not raw_query:
            return {
                "query": query,
                "detected_script": "en",
                "expanded_query": "",
                "transliteration_applied": False,
                "expanded_acronyms": [],
                "total_results": 0,
                "results": [],
                "invented_chunk_count": 0,
                "disclaimer": STATUTORY_DISCLAIMER,
            }

        # 1. Script detection and concept transliteration to English
        routing = self.router.route_query(raw_query)
        concept_query = routing.translated_concept_query

        # 2. Domain acronym expansion
        expanded_query, expanded_acronyms = expand_query_acronyms(concept_query)

        # 3. Sparse search (PostgreSQL tsvector / GIN or SQLite token overlap)
        sparse_matches = await self.repo.search_sparse(
            query_text=expanded_query, limit=top_k * 2, state_filter=state_filter
        )
        sparse_ranks: dict[Any, int] = {
            chunk.chunk_id: rank + 1 for rank, (chunk, _) in enumerate(sparse_matches)
        }

        # 4. Dense semantic search (pgvector HNSW cosine similarity)
        query_vector = local_embedder.embed_text(expanded_query)
        dense_matches = await self.repo.search_dense(
            query_vector=query_vector, limit=top_k * 2, state_filter=state_filter
        )
        dense_ranks: dict[Any, int] = {
            chunk.chunk_id: rank + 1 for rank, (chunk, _) in enumerate(dense_matches)
        }
        dense_scores: dict[Any, float] = {chunk.chunk_id: score for chunk, score in dense_matches}

        # 5. Reciprocal Rank Fusion (RRF, k=60) with relevance gating
        chunk_map: dict[Any, Any] = {}
        for ch, _ in sparse_matches:
            chunk_map[ch.chunk_id] = ch
        for ch, sim in dense_matches:
            # Only consider dense match if it meets relevance threshold or has sparse support
            if sim >= 0.52 or ch.chunk_id in chunk_map:
                chunk_map[ch.chunk_id] = ch

        if not chunk_map:
            return {
                "query": raw_query,
                "detected_script": routing.detected_script.value,
                "expanded_query": expanded_query,
                "transliteration_applied": routing.is_transliterated,
                "expanded_acronyms": expanded_acronyms,
                "total_results": 0,
                "results": [],
                "invented_chunk_count": 0,
                "disclaimer": STATUTORY_DISCLAIMER,
            }

        fused_candidates: list[dict[str, Any]] = []
        for cid, ch in chunk_map.items():
            s_rank = sparse_ranks.get(cid)
            d_rank = dense_ranks.get(cid)
            d_score = dense_scores.get(cid, 0.0)

            # Strict relevance gate: reject if zero sparse match and weak dense similarity
            if s_rank is None and d_score < 0.52:
                continue

            rrf_score = 0.0
            if s_rank is not None:
                rrf_score += 1.0 / (RRF_K + s_rank)
            if d_rank is not None and d_score >= 0.35:
                rrf_score += 1.0 / (RRF_K + d_rank)

            if rrf_score > 0.0:
                fused_candidates.append(
                    {
                        "chunk": ch,
                        "sparse_rank": s_rank,
                        "dense_rank": d_rank,
                        "rrf_score": rrf_score,
                    }
                )

        # Deterministic ranking: sort by rrf_score DESC, tie-break by chunk_id string
        fused_candidates.sort(
            key=lambda x: (x["rrf_score"], str(x["chunk"].chunk_id)), reverse=True
        )
        top_candidates = fused_candidates[:top_k]

        # 6. Attach verified official provenance
        candidates_with_provenance = await self.repo.attach_provenance(
            top_candidates, state_filter=state_filter
        )

        # 7. Dynamically compute invented chunk count by validating against source document
        invented_count = await compute_invented_chunk_count(
            self.session, candidates_with_provenance
        )

        return {
            "query": raw_query,
            "detected_script": routing.detected_script.value,
            "expanded_query": expanded_query,
            "transliteration_applied": routing.is_transliterated,
            "expanded_acronyms": expanded_acronyms,
            "total_results": len(candidates_with_provenance),
            "results": candidates_with_provenance,
            "invented_chunk_count": invented_count,
            "disclaimer": STATUTORY_DISCLAIMER,
        }
