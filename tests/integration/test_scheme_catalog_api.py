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


@pytest.mark.asyncio
async def test_catalog_filtering_restricts_to_latest_version(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify catalog filters apply strictly to the LATEST version of each scheme (Work Item R8).

    - Scheme 1: v1 had CLOSED window and GENERAL category; v2 (latest) has OPEN window and ST category.
    - Scheme 2: v1 had OPEN window and ST category; v2 (latest) has CLOSED window and OBC category.

    Filtering for portal_status=OPEN must return Scheme 1, NOT Scheme 2.
    Filtering for portal_status=CLOSED must return Scheme 2, NOT Scheme 1.
    Filtering for category=ST must return Scheme 1, NOT Scheme 2.
    Filtering for category=OBC must return Scheme 2, NOT Scheme 1.
    """
    # 1. Seed Scheme 1 (v1 CLOSED -> v2 OPEN)
    scheme_1 = Scheme(
        scheme_id="sch-mv-01",
        official_code="MV_SCH_01",
        title_en="Multi-Version Scheme 1 (Now Open)",
        issuing_level=SchemeLevel.STATE_SECTOR,
        ministry_or_department="Tribal Affairs Manipur",
        implementing_agency="Govt of Manipur",
        canonical_source_url="https://example.gov.in/sch1",
        guidelines_document_url="https://example.gov.in/sch1.pdf",
        is_active=True,
    )
    db_session.add(scheme_1)
    await db_session.flush()

    v1_s1 = SchemeVersion(
        scheme_id=scheme_1.scheme_id,
        version_number=1,
        academic_year="2023-2024",
        content_sha256="1" * 64,
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
    )
    db_session.add(v1_s1)
    await db_session.flush()
    db_session.add(
        SchemeEligibilityRule(
            version_id=v1_s1.version_id,
            target_categories=["GENERAL"],
            eligible_genders=["ANY"],
            eligible_domiciles=["ALL_INDIA"],
            eligible_course_levels=["UNDERGRADUATE"],
            ast_rule_logic={"==": [1, 1]},
            rule_description_en="Old v1 rule",
        )
    )
    db_session.add(
        SchemeApplicationWindow(
            version_id=v1_s1.version_id,
            portal_type=PortalType.STATE_DIRECT_PORTAL,
            portal_url="https://example.gov.in/old",
            portal_status=PortalWindowStatus.CLOSED,
        )
    )

    v2_s1 = SchemeVersion(
        scheme_id=scheme_1.scheme_id,
        version_number=2,
        academic_year="2024-2025",
        content_sha256="2" * 64,
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
    )
    db_session.add(v2_s1)
    await db_session.flush()
    db_session.add(
        SchemeEligibilityRule(
            version_id=v2_s1.version_id,
            target_categories=["ST"],
            eligible_genders=["ANY"],
            eligible_domiciles=["MANIPUR"],
            eligible_course_levels=["UNDERGRADUATE"],
            ast_rule_logic={"==": [1, 1]},
            rule_description_en="New v2 ST rule",
        )
    )
    db_session.add(
        SchemeApplicationWindow(
            version_id=v2_s1.version_id,
            portal_type=PortalType.STATE_DIRECT_PORTAL,
            portal_url="https://example.gov.in/new",
            portal_status=PortalWindowStatus.OPEN,
        )
    )

    # 2. Seed Scheme 2 (v1 OPEN -> v2 CLOSED)
    scheme_2 = Scheme(
        scheme_id="sch-mv-02",
        official_code="MV_SCH_02",
        title_en="Multi-Version Scheme 2 (Now Closed)",
        issuing_level=SchemeLevel.STATE_SECTOR,
        ministry_or_department="OBC Directorate Manipur",
        implementing_agency="Govt of Manipur",
        canonical_source_url="https://example.gov.in/sch2",
        guidelines_document_url="https://example.gov.in/sch2.pdf",
        is_active=True,
    )
    db_session.add(scheme_2)
    await db_session.flush()

    v1_s2 = SchemeVersion(
        scheme_id=scheme_2.scheme_id,
        version_number=1,
        academic_year="2023-2024",
        content_sha256="3" * 64,
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
    )
    db_session.add(v1_s2)
    await db_session.flush()
    db_session.add(
        SchemeEligibilityRule(
            version_id=v1_s2.version_id,
            target_categories=["ST"],
            eligible_genders=["ANY"],
            eligible_domiciles=["MANIPUR"],
            eligible_course_levels=["UNDERGRADUATE"],
            ast_rule_logic={"==": [1, 1]},
            rule_description_en="Old v1 rule ST",
        )
    )
    db_session.add(
        SchemeApplicationWindow(
            version_id=v1_s2.version_id,
            portal_type=PortalType.STATE_DIRECT_PORTAL,
            portal_url="https://example.gov.in/old2",
            portal_status=PortalWindowStatus.OPEN,
        )
    )

    v2_s2 = SchemeVersion(
        scheme_id=scheme_2.scheme_id,
        version_number=2,
        academic_year="2024-2025",
        content_sha256="4" * 64,
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
    )
    db_session.add(v2_s2)
    await db_session.flush()
    db_session.add(
        SchemeEligibilityRule(
            version_id=v2_s2.version_id,
            target_categories=["OBC"],
            eligible_genders=["ANY"],
            eligible_domiciles=["MANIPUR"],
            eligible_course_levels=["UNDERGRADUATE"],
            ast_rule_logic={"==": [1, 1]},
            rule_description_en="New v2 rule OBC",
        )
    )
    db_session.add(
        SchemeApplicationWindow(
            version_id=v2_s2.version_id,
            portal_type=PortalType.STATE_DIRECT_PORTAL,
            portal_url="https://example.gov.in/new2",
            portal_status=PortalWindowStatus.CLOSED,
        )
    )
    await db_session.commit()

    # Query 1: Filter portal_status=OPEN
    resp_open = await async_client.get("/api/v1/schemes/catalog?portal_status=OPEN")
    assert resp_open.status_code == 200
    open_ids = [it["scheme_id"] for it in resp_open.json()["items"]]
    assert "sch-mv-01" in open_ids
    assert "sch-mv-02" not in open_ids

    # Query 2: Filter portal_status=CLOSED
    resp_closed = await async_client.get("/api/v1/schemes/catalog?portal_status=CLOSED")
    assert resp_closed.status_code == 200
    closed_ids = [it["scheme_id"] for it in resp_closed.json()["items"]]
    assert "sch-mv-02" in closed_ids
    assert "sch-mv-01" not in closed_ids

    # Query 3: Filter category=OBC
    resp_obc = await async_client.get("/api/v1/schemes/catalog?category=OBC")
    assert resp_obc.status_code == 200
    obc_ids = [it["scheme_id"] for it in resp_obc.json()["items"]]
    assert "sch-mv-02" in obc_ids
    assert "sch-mv-01" not in obc_ids
