"""Postgres + pgvector Integration Tests for Hybrid Retrieval (R4 Remediation).

Verifies:
- search_sparse leveraging PostgreSQL Full-Text Search and GIN index
- search_dense with parameterized CAST(:vec AS vector) (no string interpolation)
- state_filter applied in SQL before LIMIT in both sparse and dense
- dynamic window-closed calculation using date.today()
- whitespace-only and empty queries handled gracefully with statutory disclaimer
"""

import os
import socket
from collections.abc import AsyncGenerator
from datetime import date
from urllib.parse import urlparse

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.modules.catalog.infrastructure.seed_data import seed_pilot_schemes
from src.modules.retrieval.application.corpus_seed_service import CorpusSeedService
from src.modules.retrieval.application.embedding_service import local_embedder
from src.modules.retrieval.application.retrieval_service import RetrievalService
from src.modules.retrieval.infrastructure.repositories import RetrievalRepository

PG_TEST_URL = os.getenv(
    "POSTGRES_TEST_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://schemesaathi:test162741@127.0.0.1:5432/schemesaathi_db",
    ),
)


def check_postgres_availability() -> bool:
    """Check if PostgreSQL 16 instance is reachable."""
    host = "localhost"
    port = 5432
    try:
        clean_url = PG_TEST_URL.replace("postgresql+asyncpg://", "http://").replace(
            "postgresql://", "http://"
        )
        parsed = urlparse(clean_url)
        if parsed.hostname:
            host = parsed.hostname
        if parsed.port:
            port = parsed.port
    except Exception:
        pass

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        res = sock.connect_ex((host, port))
        sock.close()
        available = res == 0
    except Exception:
        available = False

    is_ci = (
        os.getenv("CI", "").lower() in ("true", "1")
        or os.getenv("GITHUB_ACTIONS", "").lower() == "true"
    )
    if is_ci and not available:
        pytest.fail(
            f"PostgreSQL 16 + pgvector is REQUIRED in CI environment but connection to {host}:{port} failed!"
        )
    return available


skip_if_no_pg = pytest.mark.skipif(
    not check_postgres_availability(),
    reason="PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)",
)


@pytest.fixture
def pg_engine() -> AsyncEngine:
    return create_async_engine(PG_TEST_URL, echo=False)


@pytest.fixture
async def pg_session(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def setup_postgres_corpus(pg_session: AsyncSession) -> None:
    """Seed pilot schemes and guideline corpus for PostgreSQL integration testing."""
    await seed_pilot_schemes(pg_session)
    seed_svc = CorpusSeedService(pg_session)
    await seed_svc.seed_guideline_corpus()


@pytest.mark.asyncio
@skip_if_no_pg
async def test_postgres_sparse_fts_with_gin_index(pg_session: AsyncSession) -> None:
    """Verify PostgreSQL full-text search against scheme_knowledge_chunks."""
    repo = RetrievalRepository(pg_session)
    results = await repo.search_sparse(query_text="merit scholarship undergraduate", limit=5)
    assert len(results) > 0

    chunk, score = results[0]
    assert chunk.scheme_id is not None
    assert score > 0.0
    assert "merit" in chunk.chunk_content.lower() or "scholarship" in chunk.chunk_content.lower()


@pytest.mark.asyncio
@skip_if_no_pg
async def test_postgres_dense_parameterized_query(pg_session: AsyncSession) -> None:
    """Verify dense search with 1024-dim parameterized vector query."""
    repo = RetrievalRepository(pg_session)
    query_vec = local_embedder.embed_text("post-matric scholarship scheduled tribe Manipur")
    assert len(query_vec) == 1024

    results = await repo.search_dense(query_vector=query_vec, limit=5)
    assert len(results) > 0

    chunk, sim = results[0]
    assert chunk.scheme_id is not None
    assert sim > 0.30


@pytest.mark.asyncio
@skip_if_no_pg
async def test_postgres_state_filter_before_limit(pg_session: AsyncSession) -> None:
    """Verify state_filter restricts search candidates in SQL query prior to LIMIT."""
    repo = RetrievalRepository(pg_session)

    # 1. Manipur state filter should return Manipur pilot schemes
    manipur_sparse = await repo.search_sparse(
        query_text="scholarship", limit=10, state_filter="MANIPUR"
    )
    assert len(manipur_sparse) > 0
    for chunk, _ in manipur_sparse:
        assert chunk.scheme_id.startswith("SCH-MN-")

    # 2. Non-matching state filter (e.g. KARNATAKA) should return 0 results before limit
    karnataka_sparse = await repo.search_sparse(
        query_text="scholarship", limit=10, state_filter="KARNATAKA"
    )
    assert len(karnataka_sparse) == 0

    # 3. Dense search with non-matching state filter should also return 0 results
    query_vec = local_embedder.embed_text("scholarship")
    karnataka_dense = await repo.search_dense(
        query_vector=query_vec, limit=10, state_filter="KARNATAKA"
    )
    assert len(karnataka_dense) == 0


@pytest.mark.asyncio
@skip_if_no_pg
async def test_dynamic_window_closed_provenance(pg_session: AsyncSession) -> None:
    """Verify is_window_closed is evaluated dynamically against date.today()."""
    repo = RetrievalRepository(pg_session)
    chunks = await repo.get_all_chunks()
    assert len(chunks) > 0

    test_candidates = [{"chunk": chunks[0], "sparse_rank": 1, "dense_rank": 1, "rrf_score": 0.05}]
    provenance = await repo.attach_provenance(test_candidates)
    assert len(provenance) == 1

    candidate = provenance[0]
    # For 2024-2025 pilot schemes, window closed in 2024/early 2025
    assert candidate.window_close_date is not None
    assert candidate.window_close_date < date.today()
    assert candidate.is_window_closed is True


@pytest.mark.asyncio
@skip_if_no_pg
async def test_retrieval_service_whitespace_query_handling(pg_session: AsyncSession) -> None:
    """Verify RetrievalService handles whitespace queries gracefully with disclaimer."""
    service = RetrievalService(pg_session)

    res_empty = await service.search(query="   ", top_k=5)
    assert res_empty["total_results"] == 0
    assert len(res_empty["results"]) == 0
    assert res_empty["invented_chunk_count"] == 0
    assert "disclaimer" in res_empty
    assert "closed" in res_empty["disclaimer"].lower()
