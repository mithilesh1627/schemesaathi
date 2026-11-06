"""Chunk and Vector Retrieval Repository supporting PostgreSQL pgvector + GIN and SQLite fallback."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.catalog.domain.models import (
    Scheme,
    SchemeApplicationWindow,
    SchemeEligibilityRule,
    SchemeKnowledgeChunk,
    SchemeVersion,
)
from src.modules.retrieval.domain.models import RetrievalCandidate

logger = get_logger(__name__)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two unit vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    return dot


class RetrievalRepository:
    """Performs sparse keyword search, dense pgvector cosine search, and provenance attachment."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all_chunks(self) -> list[SchemeKnowledgeChunk]:
        """Fetch all stored chunks for testing or audit."""
        stmt = select(SchemeKnowledgeChunk).order_by(SchemeKnowledgeChunk.chunk_index)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def search_sparse(
        self, query_text: str, limit: int = 20, state_filter: str | None = None
    ) -> list[tuple[SchemeKnowledgeChunk, float]]:
        """Perform sparse lexical search using PostgreSQL tsvector / GIN or SQLite token match."""
        _ = state_filter
        bind = self.session.bind
        dialect_name = bind.dialect.name if bind else "postgresql"

        clean_query = query_text.strip()
        if not clean_query:
            return []

        if dialect_name == "postgresql":
            # PostgreSQL Full-Text Search with ts_rank
            ts_sql = text(
                """
                SELECT c.chunk_id,
                       ts_rank_cd(to_tsvector('english', c.chunk_content), websearch_to_tsquery('english', :q)) AS rank_score
                FROM scheme_knowledge_chunks c
                WHERE to_tsvector('english', c.chunk_content) @@ websearch_to_tsquery('english', :q)
                ORDER BY rank_score DESC
                LIMIT :limit
                """
            )
            try:
                res = await self.session.execute(ts_sql, {"q": clean_query, "limit": limit})
                rows = res.fetchall()
            except Exception:
                # Fallback to plainto_tsquery if websearch_to_tsquery encounters complex tokens
                fallback_sql = text(
                    """
                    SELECT c.chunk_id,
                           ts_rank_cd(to_tsvector('english', c.chunk_content), plainto_tsquery('english', :q)) AS rank_score
                    FROM scheme_knowledge_chunks c
                    WHERE to_tsvector('english', c.chunk_content) @@ plainto_tsquery('english', :q)
                    ORDER BY rank_score DESC
                    LIMIT :limit
                    """
                )
                res = await self.session.execute(fallback_sql, {"q": clean_query, "limit": limit})
                rows = res.fetchall()

            chunk_ids = [row[0] for row in rows]
            scores = {row[0]: float(row[1]) for row in rows}
            if not chunk_ids:
                return []

            stmt = select(SchemeKnowledgeChunk).where(SchemeKnowledgeChunk.chunk_id.in_(chunk_ids))
            res_chunks = await self.session.execute(stmt)
            chunks_by_id = {c.chunk_id: c for c in res_chunks.scalars().all()}

            return [(chunks_by_id[cid], scores[cid]) for cid in chunk_ids if cid in chunks_by_id]

        else:
            # SQLite / Mock fallback: lexical token overlap with domain stopword filtering
            raw_tokens = [t.lower() for t in clean_query.split() if len(t) > 2]
            stopwords = {"the", "and", "for", "with", "from", "scheme", "scholarship", "government"}
            meaningful_tokens = [t for t in raw_tokens if t not in stopwords]
            search_tokens = meaningful_tokens if meaningful_tokens else raw_tokens

            stmt = select(SchemeKnowledgeChunk)
            all_res = await self.session.execute(stmt)
            candidates: list[tuple[SchemeKnowledgeChunk, float]] = []

            for c in all_res.scalars().all():
                content_lower = c.chunk_content.lower()
                matches = sum(1 for tok in search_tokens if tok in content_lower)
                threshold = 1 if len(search_tokens) <= 2 else 2
                if matches >= threshold and (matches / len(search_tokens)) >= 0.30:
                    score = matches / len(search_tokens)
                    candidates.append((c, score))

            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[:limit]

    async def search_dense(
        self, query_vector: list[float], limit: int = 20, state_filter: str | None = None
    ) -> list[tuple[SchemeKnowledgeChunk, float]]:
        """Perform dense semantic search using pgvector cosine distance or Python dot product."""
        _ = state_filter
        bind = self.session.bind
        dialect_name = bind.dialect.name if bind else "postgresql"

        if dialect_name == "postgresql":
            # pgvector HNSW cosine distance search: operator `<=>`
            # Cosine distance = 1.0 - cosine_similarity. Similarity = 1.0 - distance.
            vec_literal = "[" + ",".join(str(f) for f in query_vector) + "]"
            sql = text(
                f"""
                SELECT chunk_id, (embedding <=> '{vec_literal}') as distance
                FROM scheme_knowledge_chunks
                WHERE embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT :limit
                """
            )
            res = await self.session.execute(sql, {"limit": limit})
            rows = res.fetchall()

            chunk_ids = [row[0] for row in rows]
            sim_scores = {row[0]: 1.0 - float(row[1]) for row in rows}

            if not chunk_ids:
                return []

            stmt = select(SchemeKnowledgeChunk).where(SchemeKnowledgeChunk.chunk_id.in_(chunk_ids))
            res_chunks = await self.session.execute(stmt)
            chunks_by_id = {c.chunk_id: c for c in res_chunks.scalars().all()}

            return [
                (chunks_by_id[cid], sim_scores[cid]) for cid in chunk_ids if cid in chunks_by_id
            ]

        else:
            # SQLite fallback: in-memory cosine similarity
            stmt = select(SchemeKnowledgeChunk).where(SchemeKnowledgeChunk.embedding.is_not(None))
            res = await self.session.execute(stmt)
            all_chunks = res.scalars().all()

            scored: list[tuple[SchemeKnowledgeChunk, float]] = []
            for ch in all_chunks:
                if ch.embedding:
                    sim = _cosine_similarity(query_vector, list(ch.embedding))
                    scored.append((ch, sim))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:limit]

    async def attach_provenance(
        self,
        scored_candidates: list[dict[str, Any]],
        state_filter: str | None = None,
    ) -> list[RetrievalCandidate]:
        """Attach official source URL, document SHA-256, academic year, and closed window status."""
        if not scored_candidates:
            return []

        chunk_ids = [sc["chunk"].chunk_id for sc in scored_candidates]

        # Query chunk joined with version, scheme, window, and rule
        stmt = (
            select(
                SchemeKnowledgeChunk,
                SchemeVersion,
                Scheme,
                SchemeApplicationWindow,
                SchemeEligibilityRule,
            )
            .join(SchemeVersion, SchemeKnowledgeChunk.version_id == SchemeVersion.version_id)
            .join(Scheme, SchemeKnowledgeChunk.scheme_id == Scheme.scheme_id)
            .outerjoin(
                SchemeApplicationWindow,
                SchemeVersion.version_id == SchemeApplicationWindow.version_id,
            )
            .outerjoin(
                SchemeEligibilityRule,
                SchemeVersion.version_id == SchemeEligibilityRule.version_id,
            )
            .where(SchemeKnowledgeChunk.chunk_id.in_(chunk_ids))
        )

        res = await self.session.execute(stmt)
        prov_map: dict[
            uuid.UUID,
            tuple[
                SchemeVersion | None,
                Scheme | None,
                SchemeApplicationWindow | None,
                SchemeEligibilityRule | None,
            ],
        ] = {}
        for row in res.all():
            prov_map[row[0].chunk_id] = (row[1], row[2], row[3], row[4])

        today = date(2026, 11, 5)  # Statutory audit reference date
        results: list[RetrievalCandidate] = []

        for item in scored_candidates:
            chunk: SchemeKnowledgeChunk = item["chunk"]
            mapping_val: tuple[
                SchemeVersion | None,
                Scheme | None,
                SchemeApplicationWindow | None,
                SchemeEligibilityRule | None,
            ] = prov_map.get(chunk.chunk_id, (None, None, None, None))
            ver, sch, win, rle = mapping_val

            # Apply state filter if provided (Pan-India guardrail)
            if state_filter and rle:
                domiciles = (
                    rle.eligible_domiciles if isinstance(rle.eligible_domiciles, list) else []
                )
                if (
                    state_filter.upper() not in domiciles
                    and "ALL_INDIA" not in domiciles
                    and "ALL" not in domiciles
                ):
                    continue

            doc_sha = ver.content_sha256 if ver else chunk.content_sha256
            source_url = sch.guidelines_document_url if sch else ""
            academic_year = ver.academic_year if ver else "2024-2025"

            window_open = win.window_open_date if win else None
            window_close = win.window_close_date if win else None
            portal_status = win.portal_status.value if win else "CLOSED"

            # Check if window has passed
            is_closed = True
            if window_close and window_close >= today:
                is_closed = False

            results.append(
                RetrievalCandidate(
                    chunk_id=chunk.chunk_id,
                    scheme_id=chunk.scheme_id,
                    version_id=chunk.version_id,
                    section_title=chunk.section_title,
                    chunk_content=chunk.chunk_content,
                    token_count=chunk.token_count,
                    page_number=chunk.page_number,
                    source_url=source_url,
                    document_sha256=doc_sha,
                    academic_year=academic_year,
                    window_open_date=window_open,
                    window_close_date=window_close,
                    portal_status=portal_status,
                    is_window_closed=is_closed,
                    sparse_rank=item.get("sparse_rank"),
                    dense_rank=item.get("dense_rank"),
                    rrf_score=item.get("rrf_score", 0.0),
                )
            )

        return results
