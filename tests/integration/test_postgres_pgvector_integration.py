"""Integration Tests against Real PostgreSQL 16 + pgvector Instance."""

import os
import socket
import uuid
from collections.abc import Iterator
from urllib.parse import urlparse

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.modules.catalog.domain.enums import (
    PortalType,
    PortalWindowStatus,
    SchemeLevel,
    VerificationStatus,
)
from src.modules.catalog.domain.models import (
    Scheme,
    SchemeApplicationWindow,
    SchemeEligibilityRule,
    SchemeKnowledgeChunk,
    SchemeVersion,
)
from src.modules.catalog.infrastructure.repositories import SchemeRepository

PG_TEST_URL = os.getenv(
    "POSTGRES_TEST_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://schemesaathi:schemesaathi_dev_password@localhost:5432/schemesaathi_db",
    ),
)


def check_postgres_availability() -> bool:
    """Check if PostgreSQL 16 instance is reachable. In CI, failure to connect fails the test suite."""
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
def pg_engine() -> Iterator[AsyncEngine]:
    engine = create_async_engine(PG_TEST_URL, echo=False)
    yield engine


@pytest.mark.asyncio
@skip_if_no_pg
async def test_postgres_extensions_and_vector_operations(pg_engine: AsyncEngine) -> None:
    """Verify PostgreSQL 16 pgvector, pgcrypto, uuid-ossp, and 1536-dim vector search."""
    session_factory = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    async with session_factory() as session:
        # 1. Verify extensions
        ext_res = await session.execute(
            text(
                "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pgcrypto')"
            )
        )
        installed_exts = {row[0] for row in ext_res.fetchall()}
        assert "vector" in installed_exts
        assert "uuid-ossp" in installed_exts
        assert "pgcrypto" in installed_exts

        # 2. Setup scheme and version
        test_id = f"sch-pg-{uuid.uuid4().hex[:8]}"
        scheme = Scheme(
            scheme_id=test_id,
            official_code=f"OFF_{test_id}",
            title_en="Postgres Vector Integration Scheme",
            issuing_level=SchemeLevel.CENTRAL_SECTOR,
            ministry_or_department="Ministry of Tribal Affairs",
            implementing_agency="Central Directorate",
            canonical_source_url="https://tribal.nic.in",
            guidelines_document_url="https://tribal.nic.in/guidelines.pdf",
            is_active=True,
        )
        session.add(scheme)
        await session.flush()

        version = SchemeVersion(
            scheme_id=scheme.scheme_id,
            version_number=1,
            academic_year="2024-2025",
            content_sha256="c" * 64,
            verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        )
        session.add(version)
        await session.flush()

        # 3. Insert Knowledge Chunks with 1536-dim embeddings and metadata
        chunk1 = SchemeKnowledgeChunk(
            version_id=version.version_id,
            scheme_id=scheme.scheme_id,
            language_code="en",
            section_title="Income Ceiling Rule",
            chunk_content="Family income must not exceed 2.50 lakh per annum for ST students.",
            token_count=14,
            embedding=[0.01] * 1536,
            embedding_model="text-embedding-3-small",
            embedding_dimension=1536,
            model_version="v1",
            content_sha256="1" * 64,
        )
        chunk2 = SchemeKnowledgeChunk(
            version_id=version.version_id,
            scheme_id=scheme.scheme_id,
            language_code="en",
            section_title="Day Scholar Allowance",
            chunk_content="Day scholar maintenance allowance is rupees 7000 annually.",
            token_count=10,
            embedding=[0.85] * 1536,
            embedding_model="text-embedding-3-small",
            embedding_dimension=1536,
            model_version="v1",
            content_sha256="2" * 64,
        )
        session.add_all([chunk1, chunk2])
        await session.commit()

        # 4. Perform cosine distance search
        query_vector = [0.01] * 1536
        stmt = (
            select(SchemeKnowledgeChunk)
            .where(SchemeKnowledgeChunk.scheme_id == test_id)
            .order_by(SchemeKnowledgeChunk.embedding.cosine_distance(query_vector))
            .limit(1)
        )
        result = await session.execute(stmt)
        closest_chunk = result.scalar_one()

        assert closest_chunk.section_title == "Income Ceiling Rule"
        assert closest_chunk.embedding_model == "text-embedding-3-small"
        assert closest_chunk.embedding_dimension == 1536
        assert closest_chunk.model_version == "v1"

        # 5. Clean up via CASCADE delete on parent scheme
        await session.delete(scheme)
        await session.commit()

        # Verify cascading deletion of chunks
        chunks_left = await session.execute(
            select(SchemeKnowledgeChunk).where(SchemeKnowledgeChunk.scheme_id == test_id)
        )
        assert len(chunks_left.scalars().all()) == 0


@pytest.mark.asyncio
@skip_if_no_pg
async def test_postgres_gin_indexing_and_jsonb_queries(pg_engine: AsyncEngine) -> None:
    """Verify GIN-indexed JSONB containment queries and ENUM constraints on PostgreSQL 16."""
    session_factory = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    async with session_factory() as session:
        test_id = f"sch-gin-{uuid.uuid4().hex[:8]}"
        scheme = Scheme(
            scheme_id=test_id,
            official_code=f"GIN_{test_id}",
            title_en="GIN Index Verification Scheme",
            issuing_level=SchemeLevel.STATE_SECTOR,
            ministry_or_department="Manipur Higher Education",
            implementing_agency="Govt of Manipur",
            canonical_source_url="https://example.gov.in",
            guidelines_document_url="https://example.gov.in/doc.pdf",
            is_active=True,
        )
        session.add(scheme)
        await session.flush()

        ver = SchemeVersion(
            scheme_id=scheme.scheme_id,
            version_number=1,
            academic_year="2024-2025",
            content_sha256="d" * 64,
            verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        )
        session.add(ver)
        await session.flush()

        rule = SchemeEligibilityRule(
            version_id=ver.version_id,
            income_ceiling_annual_inr=300000.00,
            minimum_qualifying_marks_percent=60.00,
            target_categories=["ST", "OBC"],
            eligible_genders=["ANY"],
            eligible_domiciles=["MANIPUR"],
            eligible_course_levels=["UNDERGRADUATE"],
            ast_rule_logic={"and": [{"<=": [{"var": "income"}, 300000]}]},
            rule_description_en="ST and OBC students of Manipur",
        )
        session.add(rule)

        window = SchemeApplicationWindow(
            version_id=ver.version_id,
            portal_type=PortalType.STATE_DIRECT_PORTAL,
            portal_url="https://example.gov.in/apply",
            portal_status=PortalWindowStatus.OPEN,
        )
        session.add(window)
        await session.commit()

        # Execute PostgreSQL JSONB containment query utilizing GIN index
        gin_query = text(
            "SELECT rule_id FROM scheme_eligibility_rules WHERE target_categories @> '[\"ST\"]'::jsonb"
        )
        gin_res = await session.execute(gin_query)
        matching_rule_ids = [str(r[0]) for r in gin_res.fetchall()]
        assert str(rule.rule_id) in matching_rule_ids

        # Clean up
        await session.delete(scheme)
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_scheme_repository_latest_version_and_gin_containment(
    pg_engine: AsyncEngine,
) -> None:
    """Verify SchemeRepository on PostgreSQL 16 restricts queries to latest version and uses JSONB GIN containment."""
    if not check_postgres_availability():
        if os.getenv("CI") == "true":
            pytest.fail(
                "PostgreSQL 16 + pgvector instance is required in CI but is currently unreachable."
            )
        pytest.skip("PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)")

    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)

    prefix = uuid.uuid4().hex[:6]
    sch1_id = f"sch-pg-mv1-{prefix}"
    sch2_id = f"sch-pg-mv2-{prefix}"

    async with session_factory() as session:
        repo = SchemeRepository(session)

        # 1. Scheme 1: v1 (CLOSED, GENERAL) -> v2 (OPEN, ST)
        s1 = Scheme(
            scheme_id=sch1_id,
            official_code=f"CODE_{sch1_id}",
            title_en="Postgres MV 1 (Open ST)",
            issuing_level=SchemeLevel.STATE_SECTOR,
            ministry_or_department="Tribal Affairs Manipur",
            implementing_agency="Govt of Manipur",
            canonical_source_url="https://example.gov.in/1",
            guidelines_document_url="https://example.gov.in/1.pdf",
            is_active=True,
        )
        session.add(s1)
        await session.flush()

        v1_s1 = SchemeVersion(
            scheme_id=s1.scheme_id,
            version_number=1,
            academic_year="2023-2024",
            content_sha256=f"sha_v1_{prefix}",
            verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        )
        session.add(v1_s1)
        await session.flush()
        session.add(
            SchemeEligibilityRule(
                version_id=v1_s1.version_id,
                target_categories=["GENERAL"],
                eligible_genders=["ANY"],
                eligible_domiciles=["ALL_INDIA"],
                eligible_course_levels=["UNDERGRADUATE"],
                ast_rule_logic={"==": [1, 1]},
                rule_description_en="Old rule",
            )
        )
        session.add(
            SchemeApplicationWindow(
                version_id=v1_s1.version_id,
                portal_type=PortalType.STATE_DIRECT_PORTAL,
                portal_url="https://example.gov.in/old",
                portal_status=PortalWindowStatus.CLOSED,
            )
        )

        v2_s1 = SchemeVersion(
            scheme_id=s1.scheme_id,
            version_number=2,
            academic_year="2024-2025",
            content_sha256=f"sha_v2_{prefix}",
            verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        )
        session.add(v2_s1)
        await session.flush()
        session.add(
            SchemeEligibilityRule(
                version_id=v2_s1.version_id,
                target_categories=["ST", "SC"],
                eligible_genders=["ANY"],
                eligible_domiciles=["MANIPUR"],
                eligible_course_levels=["UNDERGRADUATE"],
                ast_rule_logic={"==": [1, 1]},
                rule_description_en="New ST rule",
            )
        )
        session.add(
            SchemeApplicationWindow(
                version_id=v2_s1.version_id,
                portal_type=PortalType.STATE_DIRECT_PORTAL,
                portal_url="https://example.gov.in/new",
                portal_status=PortalWindowStatus.OPEN,
            )
        )

        # 2. Scheme 2: v1 (OPEN, ST) -> v2 (CLOSED, OBC)
        s2 = Scheme(
            scheme_id=sch2_id,
            official_code=f"CODE_{sch2_id}",
            title_en="Postgres MV 2 (Closed OBC)",
            issuing_level=SchemeLevel.STATE_SECTOR,
            ministry_or_department="OBC Directorate Manipur",
            implementing_agency="Govt of Manipur",
            canonical_source_url="https://example.gov.in/2",
            guidelines_document_url="https://example.gov.in/2.pdf",
            is_active=True,
        )
        session.add(s2)
        await session.flush()

        v1_s2 = SchemeVersion(
            scheme_id=s2.scheme_id,
            version_number=1,
            academic_year="2023-2024",
            content_sha256=f"sha_v1_s2_{prefix}",
            verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        )
        session.add(v1_s2)
        await session.flush()
        session.add(
            SchemeEligibilityRule(
                version_id=v1_s2.version_id,
                target_categories=["ST"],
                eligible_genders=["ANY"],
                eligible_domiciles=["MANIPUR"],
                eligible_course_levels=["UNDERGRADUATE"],
                ast_rule_logic={"==": [1, 1]},
                rule_description_en="Old ST rule",
            )
        )
        session.add(
            SchemeApplicationWindow(
                version_id=v1_s2.version_id,
                portal_type=PortalType.STATE_DIRECT_PORTAL,
                portal_url="https://example.gov.in/old2",
                portal_status=PortalWindowStatus.OPEN,
            )
        )

        v2_s2 = SchemeVersion(
            scheme_id=s2.scheme_id,
            version_number=2,
            academic_year="2024-2025",
            content_sha256=f"sha_v2_s2_{prefix}",
            verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        )
        session.add(v2_s2)
        await session.flush()
        session.add(
            SchemeEligibilityRule(
                version_id=v2_s2.version_id,
                target_categories=["OBC"],
                eligible_genders=["ANY"],
                eligible_domiciles=["MANIPUR"],
                eligible_course_levels=["UNDERGRADUATE"],
                ast_rule_logic={"==": [1, 1]},
                rule_description_en="New OBC rule",
            )
        )
        session.add(
            SchemeApplicationWindow(
                version_id=v2_s2.version_id,
                portal_type=PortalType.STATE_DIRECT_PORTAL,
                portal_url="https://example.gov.in/new2",
                portal_status=PortalWindowStatus.CLOSED,
            )
        )
        await session.commit()

        # Test A: Filter portal_status=OPEN
        open_items, _ = await repo.list_schemes(portal_status=PortalWindowStatus.OPEN)
        open_ids = [it.scheme_id for it in open_items]
        assert sch1_id in open_ids
        assert sch2_id not in open_ids  # v1 was open, but current v2 is closed!

        # Test B: Filter portal_status=CLOSED
        closed_items, _ = await repo.list_schemes(portal_status=PortalWindowStatus.CLOSED)
        closed_ids = [it.scheme_id for it in closed_items]
        assert sch2_id in closed_ids
        assert sch1_id not in closed_ids

        # Test C: Filter category=ST (uses PostgreSQL JSONB containment @>)
        st_items, _ = await repo.list_schemes(category="ST")
        st_ids = [it.scheme_id for it in st_items]
        assert sch1_id in st_ids
        assert sch2_id not in st_ids  # v1 had ST, but current v2 is OBC!

        # Test D: Filter category=OBC (uses PostgreSQL JSONB containment @>)
        obc_items, _ = await repo.list_schemes(category="OBC")
        obc_ids = [it.scheme_id for it in obc_items]
        assert sch2_id in obc_ids
        assert sch1_id not in obc_ids

        # Clean up
        await session.delete(s1)
        await session.delete(s2)
        await session.commit()
