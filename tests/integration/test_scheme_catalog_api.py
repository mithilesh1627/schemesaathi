"""Integration Tests for Scheme Catalog Endpoints."""

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
    SchemeVersion,
)


@pytest.mark.asyncio
async def test_create_and_get_scheme(async_client: AsyncClient) -> None:
    """Verify creating a scheme and fetching it by ID."""
    payload = {
        "scheme_id": "sch-mn-test-01",
        "official_code": "MN_TEST_01",
        "title_en": "Manipur Engineering Talent Scholarship",
        "title_hi": "मणिपुर इंजीनियरिंग प्रतिभा छात्रवृत्ति",
        "title_mni_beng": "ꯃꯅꯤꯄꯨꯔ ꯏꯟꯖꯤꯅꯤꯌꯔꯤꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ",
        "issuing_level": "STATE_SECTOR",
        "ministry_or_department": "Directorate of University & Higher Education, Manipur",
        "implementing_agency": "Government of Manipur",
        "canonical_source_url": "https://highereducationmanipur.gov.in",
        "guidelines_document_url": "https://scholarships.gov.in",
        "is_active": True,
    }

    # 1. Create scheme
    create_resp = await async_client.post("/api/v1/schemes/", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["scheme_id"] == "sch-mn-test-01"
    assert created_data["official_code"] == "MN_TEST_01"

    # 2. Fetch scheme by ID
    get_resp = await async_client.get("/api/v1/schemes/sch-mn-test-01")
    assert get_resp.status_code == 200
    detail_data = get_resp.json()
    assert detail_data["scheme_id"] == "sch-mn-test-01"
    assert detail_data["title_en"] == "Manipur Engineering Talent Scholarship"


@pytest.mark.asyncio
async def test_duplicate_scheme_id_rejected(async_client: AsyncClient) -> None:
    """Verify attempting to recreate an existing scheme ID returns HTTP 400."""
    payload = {
        "scheme_id": "sch-mn-dup-test",
        "official_code": "MN_DUP_01",
        "title_en": "Duplicate Test Scheme",
        "issuing_level": "STATE_SECTOR",
        "ministry_or_department": "Education Department",
        "implementing_agency": "State Govt",
        "canonical_source_url": "https://example.gov.in",
        "guidelines_document_url": "https://example.gov.in/doc.pdf",
        "is_active": True,
    }

    resp1 = await async_client.post("/api/v1/schemes/", json=payload)
    assert resp1.status_code == 201

    resp2 = await async_client.post("/api/v1/schemes/", json=payload)
    assert resp2.status_code == 400
    err = resp2.json()
    assert err["error_code"] == "ERR_INVALID_STATE"


@pytest.mark.asyncio
async def test_get_nonexistent_scheme_returns_404(async_client: AsyncClient) -> None:
    """Verify requesting an unknown scheme ID returns HTTP 404."""
    response = await async_client.get("/api/v1/schemes/sch-nonexistent-999")
    assert response.status_code == 404
    err = response.json()
    assert err["error_code"] == "ERR_ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_paginated_catalog_listing(async_client: AsyncClient) -> None:
    """Verify /api/v1/schemes/catalog returns a paginated list with total count."""
    response = await async_client.get("/api/v1/schemes/catalog?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "items" in data
    assert data["page"] == 1
    assert data["limit"] == 10


@pytest.mark.asyncio
async def test_catalog_filtering_and_nested_statutory_data(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify statutory filters (category, domicile, portal_status) and detail responses."""
    # 1. Scheme A: Manipur ST Post-Matric (OPEN, ST/SC, Manipur, Undergrad)
    scheme_a = Scheme(
        scheme_id="sch-mn-filter-st",
        official_code="MN_ST_FILTER",
        title_en="Manipur ST Post-Matric Filter Scheme",
        issuing_level=SchemeLevel.CENTRALLY_SPONSORED,
        ministry_or_department="Department of Tribal Affairs, Manipur",
        implementing_agency="Govt of Manipur",
        canonical_source_url="https://tahmanipur.gov.in",
        guidelines_document_url="https://tahmanipur.gov.in/st.pdf",
        is_active=True,
    )
    db_session.add(scheme_a)
    await db_session.flush()

    ver_a = SchemeVersion(
        scheme_id=scheme_a.scheme_id,
        version_number=1,
        academic_year="2024-2025",
        content_sha256="a" * 64,
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
    )
    db_session.add(ver_a)
    await db_session.flush()

    rule_a = SchemeEligibilityRule(
        version_id=ver_a.version_id,
        income_ceiling_annual_inr=250000.00,
        minimum_qualifying_marks_percent=50.00,
        target_categories=["ST", "SC"],
        eligible_genders=["ANY"],
        eligible_domiciles=["MANIPUR"],
        eligible_course_levels=["UNDERGRADUATE"],
        ast_rule_logic={"and": [{"<=": [{"var": "income"}, 250000]}]},
        rule_description_en="ST Students of Manipur with family income <= 2.5 LPA",
    )
    db_session.add(rule_a)

    window_a = SchemeApplicationWindow(
        version_id=ver_a.version_id,
        portal_type=PortalType.STATE_DIRECT_PORTAL,
        portal_url="https://tahmanipur.gov.in/apply",
        portal_status=PortalWindowStatus.OPEN,
    )
    db_session.add(window_a)

    # 2. Scheme B: Central Merit Scheme (CLOSED, GENERAL, All-India, Postgrad)
    scheme_b = Scheme(
        scheme_id="sch-central-general",
        official_code="CENTRAL_GEN_FILTER",
        title_en="Central General Postgraduate Scholarship",
        issuing_level=SchemeLevel.CENTRAL_SECTOR,
        ministry_or_department="Ministry of Education",
        implementing_agency="Central Govt",
        canonical_source_url="https://scholarships.gov.in",
        guidelines_document_url="https://scholarships.gov.in/gen.pdf",
        is_active=True,
    )
    db_session.add(scheme_b)
    await db_session.flush()

    ver_b = SchemeVersion(
        scheme_id=scheme_b.scheme_id,
        version_number=1,
        academic_year="2024-2025",
        content_sha256="b" * 64,
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
    )
    db_session.add(ver_b)
    await db_session.flush()

    rule_b = SchemeEligibilityRule(
        version_id=ver_b.version_id,
        income_ceiling_annual_inr=800000.00,
        minimum_qualifying_marks_percent=75.00,
        target_categories=["GENERAL"],
        eligible_genders=["ANY"],
        eligible_domiciles=["ALL_INDIA"],
        eligible_course_levels=["POSTGRADUATE"],
        ast_rule_logic={"and": [{"<=": [{"var": "income"}, 800000]}]},
        rule_description_en="Postgraduate students with income <= 8 LPA",
    )
    db_session.add(rule_b)

    window_b = SchemeApplicationWindow(
        version_id=ver_b.version_id,
        portal_type=PortalType.NSP_2_0,
        portal_url="https://scholarships.gov.in",
        portal_status=PortalWindowStatus.CLOSED,
    )
    db_session.add(window_b)
    await db_session.commit()

    # Test 1: Filter by category=ST -> Scheme A only
    resp_st = await async_client.get("/api/v1/schemes/catalog?category=ST")
    assert resp_st.status_code == 200
    data_st = resp_st.json()
    assert data_st["total"] == 1
    item_st = data_st["items"][0]
    assert item_st["scheme_id"] == "sch-mn-filter-st"
    assert item_st["portal_status"] == "OPEN"
    assert item_st["income_ceiling_annual_inr"] == 250000.0

    # Test 2: Filter by portal_status=CLOSED -> Scheme B only
    resp_closed = await async_client.get("/api/v1/schemes/catalog?portal_status=CLOSED")
    assert resp_closed.status_code == 200
    data_closed = resp_closed.json()
    assert data_closed["total"] == 1
    assert data_closed["items"][0]["scheme_id"] == "sch-central-general"

    # Test 3: Filter by domicile=MANIPUR -> Scheme A only
    resp_dom = await async_client.get("/api/v1/schemes/catalog?domicile=MANIPUR")
    assert resp_dom.status_code == 200
    data_dom = resp_dom.json()
    assert any(it["scheme_id"] == "sch-mn-filter-st" for it in data_dom["items"])

    # Test 4: Fetch scheme detail with nested components
    resp_detail = await async_client.get("/api/v1/schemes/sch-mn-filter-st")
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert len(detail["versions"]) == 1
    v = detail["versions"][0]
    assert v["eligibility_rule"]["income_ceiling_annual_inr"] == 250000.0
    assert "ST" in v["eligibility_rule"]["target_categories"]
    assert v["application_window"]["portal_status"] == "OPEN"
