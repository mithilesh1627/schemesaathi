"""Integration and Golden Retrieval Tests against Public Hybrid Search API."""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.modules.catalog.infrastructure.seed_data import seed_pilot_schemes
from src.modules.retrieval.application.corpus_seed_service import CorpusSeedService
from src.modules.retrieval.application.embedding_service import local_embedder


@pytest.fixture(autouse=True)
async def setup_corpus(db_session: AsyncSession) -> None:
    """Ensure pilot schemes and guideline corpus are seeded and indexed before tests run."""
    await seed_pilot_schemes(db_session)
    seed_service = CorpusSeedService(db_session)
    await seed_service.seed_guideline_corpus()


@pytest.mark.asyncio
async def test_golden_english_query_top5(async_client: AsyncClient) -> None:
    """Verify English query retrieves correct scheme in top 5 candidates."""
    # Query 1: Post-Matric ST
    resp1 = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "Post-Matric ST scholarship income limit Manipur", "top_k": 5},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total_results"] > 0
    assert data1["invented_chunk_count"] == 0
    top_scheme_ids = [r["scheme_id"] for r in data1["results"]]
    assert "SCH-MN-005" in top_scheme_ids[:5]

    # Query 2: State Merit 60% marks
    resp2 = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "State Merit Scholarship marks 60%", "top_k": 5},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total_results"] > 0
    assert data2["invented_chunk_count"] == 0
    top_scheme_ids_2 = [r["scheme_id"] for r in data2["results"]]
    assert "SCH-MN-001" in top_scheme_ids_2[:5]


@pytest.mark.asyncio
async def test_golden_table_query_intact_preservation(async_client: AsyncClient) -> None:
    """Verify table queries return intact non-splittable table chunks with slab columns."""
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={
            "query": "Post-Matric ST maintenance allowance hosteller day scholar slab",
            "top_k": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_results"] > 0
    assert data["invented_chunk_count"] == 0

    # Must return the intact maintenance allowance table chunk in top candidates
    target_chunk = next(
        r
        for r in data["results"][:5]
        if r["scheme_id"] == "SCH-MN-005" and "Maintenance Allowance Slabs" in r["section_title"]
    )
    assert "| Group |" in target_chunk["chunk_content"]
    assert "Group 1" in target_chunk["chunk_content"]
    assert "Group 4" in target_chunk["chunk_content"]
    assert "13,500" in target_chunk["chunk_content"]


@pytest.mark.asyncio
async def test_golden_romanized_meiteilon_query(async_client: AsyncClient) -> None:
    """Verify Romanized Meiteilon query retrieves correct scheme in top 5."""
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "Manipur ST post-matric matung skolarsip income", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_results"] > 0
    assert data["invented_chunk_count"] == 0
    top_schemes = [r["scheme_id"] for r in data["results"][:5]]
    assert "SCH-MN-005" in top_schemes


@pytest.mark.asyncio
async def test_golden_bengali_script_query(async_client: AsyncClient) -> None:
    """Verify Bengali-script Manipuri query is detected and retrieves correct scheme in top 5."""
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "মণিপুর এস.টি মেট্রিক মতুং স্কোলারশিপ", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected_script"] == "mni-Beng"
    assert data["transliteration_applied"] is True
    assert data["total_results"] > 0
    assert data["invented_chunk_count"] == 0
    top_schemes = [r["scheme_id"] for r in data["results"][:5]]
    assert "SCH-MN-005" in top_schemes


@pytest.mark.asyncio
async def test_golden_meetei_mayek_query(async_client: AsyncClient) -> None:
    """Verify Meetei Mayek script query is detected and retrieves correct scheme in top 5."""
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "ꯃꯅꯤꯄꯨꯔ ꯑꯦꯁ.ꯇꯤ. ꯃꯦꯠꯔꯤꯛ ꯃꯇꯨꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected_script"] == "mni-Mtei"
    assert data["transliteration_applied"] is True
    assert data["total_results"] > 0
    assert data["invented_chunk_count"] == 0
    top_schemes = [r["scheme_id"] for r in data["results"][:5]]
    assert "SCH-MN-005" in top_schemes


@pytest.mark.asyncio
async def test_golden_acronym_query_expansion(async_client: AsyncClient) -> None:
    """Verify domain acronym query expands and retrieves relevant statutory chunks."""
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "NSP OTR Face RD registration", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["expanded_acronyms"]) >= 3
    assert "National Scholarship Portal" in data["expanded_query"]
    assert "One Time Registration" in data["expanded_query"]
    assert data["total_results"] > 0
    assert data["invented_chunk_count"] == 0


@pytest.mark.asyncio
async def test_golden_closed_window_surfacing(async_client: AsyncClient) -> None:
    """Verify closed application window dates are visibly surfaced on retrieved chunks."""
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "Pre-Matric ST scholarship Manipur class 9 10", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_results"] > 0

    # Pre-Matric ST window closed on 2024-10-31
    target_chunk = next(r for r in data["results"] if r["scheme_id"] == "SCH-MN-006")
    assert target_chunk["application_window"]["is_window_closed"] is True
    assert target_chunk["application_window"]["window_close_date"] == "2024-10-31"


@pytest.mark.asyncio
async def test_golden_non_matching_query_zero_invented_chunks(async_client: AsyncClient) -> None:
    """Verify non-matching query returns empty results with exactly 0 invented chunks."""
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={
            "query": "non existent quantum astrophysics supernova scholarship scheme 99999",
            "top_k": 10,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_results"] == 0
    assert len(data["results"]) == 0
    assert data["invented_chunk_count"] == 0


@pytest.mark.asyncio
async def test_pan_india_state_agnostic_fixture_query(
    db_session: AsyncSession, async_client: AsyncClient
) -> None:
    """Verify pipeline is state-agnostic by querying a non-Manipur test fixture chunk."""
    # 1. Insert a test fixture scheme and chunk for Assam / Central
    fixture_scheme_id = "TEST-AS-001"
    fixture_scheme = Scheme(
        scheme_id=fixture_scheme_id,
        official_code="AS-HE-TEST",
        title_en="Assam Higher Secondary Combined Scholarship",
        issuing_level=SchemeLevel.STATE_SECTOR,
        ministry_or_department="Directorate of Higher Education, Government of Assam",
        implementing_agency="DHE Assam",
        canonical_source_url="https://dheassam.gov.in",
        guidelines_document_url="https://dheassam.gov.in/guidelines/assam_hs_scholarship.pdf",
    )
    db_session.add(fixture_scheme)

    ver_id = uuid.uuid4()
    fixture_version = SchemeVersion(
        version_id=ver_id,
        scheme_id=fixture_scheme_id,
        version_number=1,
        academic_year="2024-2025",
        content_sha256="aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
        lifecycle_state="EXTRACTED",
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
    )
    db_session.add(fixture_version)

    fixture_window = SchemeApplicationWindow(
        version_id=ver_id,
        portal_type=PortalType.STATE_DIRECT_PORTAL,
        portal_url="https://dheassam.gov.in",
        portal_status=PortalWindowStatus.CLOSED,
        window_open_date=date(2024, 7, 1),
        window_close_date=date(2024, 11, 30),
    )
    db_session.add(fixture_window)

    fixture_rule = SchemeEligibilityRule(
        version_id=ver_id,
        income_ceiling_annual_inr=200000.0,
        target_categories=["ALL"],
        eligible_domiciles=["ASSAM"],
        eligible_course_levels=["HIGHER_SECONDARY"],
        ast_rule_logic={"==": [{"var": "domicile_state"}, "ASSAM"]},
        rule_description_en="Assam domicile, Higher Secondary course.",
    )
    db_session.add(fixture_rule)

    fixture_content = (
        "[Scheme: Assam Higher Secondary Combined Scholarship | Section: Domicile and Scope | Academic Year: 2024-2025]\n\n"
        "Directorate of Higher Education, Assam. Financial scholarship for students domiciled in the State of Assam."
    )
    emb = local_embedder.embed_text(fixture_content)
    fixture_chunk = SchemeKnowledgeChunk(
        chunk_id=uuid.uuid4(),
        version_id=ver_id,
        scheme_id=fixture_scheme_id,
        language_code="en",
        section_title="Domicile and Scope",
        chunk_content=fixture_content,
        token_count=35,
        embedding=emb,
        embedding_model=local_embedder.model_name,
        embedding_dimension=1536,
        model_version="v1",
        content_sha256="112233445566778899aabbccddeeff00112233445566778899aabbccddeeff00",
    )
    db_session.add(fixture_chunk)
    await db_session.commit()

    # 2. Query the non-Manipur test fixture
    resp = await async_client.post(
        "/api/v1/retrieval/search",
        json={"query": "Assam Higher Secondary Combined Scholarship domicile Assam", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_results"] > 0
    top_schemes = [r["scheme_id"] for r in data["results"][:5]]
    assert fixture_scheme_id in top_schemes
    assert data["invented_chunk_count"] == 0
