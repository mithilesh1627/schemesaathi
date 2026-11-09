"""Integration Tests for Eligibility Evaluation API & Demo Webpage.

Verifies:
- POST /api/v1/eligibility/evaluate end-to-end execution
- GET /demo static demo webpage with mandatory pilot disclaimer
- Strict zero-Aadhaar PII protection on request inputs, errors, and logs
- Audit trail persistence in user_evaluations and evaluation_rule_results tables
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
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
    UserEvaluation,
)
from src.modules.catalog.infrastructure.seed_data import seed_pilot_schemes


@pytest.mark.asyncio
async def test_demo_webpage_loads_with_pilot_disclaimer(async_client: AsyncClient) -> None:
    """Verify /demo endpoint serves the HTML demo with required pilot disclaimer."""
    response = await async_client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert (
        "Demo — Manipur pilot. Not a public launch. Results are indicative and must be confirmed on the official portal."
        in body
    )
    assert "SchemeSaathi Eligibility Evaluator" in body
    assert "Evaluate Statutory Eligibility" in body


@pytest.mark.asyncio
async def test_evaluate_endpoint_end_to_end(
    db_session: AsyncSession, async_client: AsyncClient
) -> None:
    """Verify POST /api/v1/eligibility/evaluate against seeded Manipur schemes."""
    # Ensure pilot schemes are seeded in this session
    await seed_pilot_schemes(db_session)

    payload = {
        "domicile_state": "MANIPUR",
        "social_category": "ST",
        "annual_family_income_inr": 200000.0,
        "course_level": "UNDERGRADUATE",
        "marks_percent": 75.0,
        "gender": "FEMALE",
        "is_displaced": False,
        "session_id": "test-session-integ-1",
    }

    response = await async_client.post("/api/v1/eligibility/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_schemes_checked"] >= 5
    assert data["total_eligible"] >= 1
    assert "schemes" in data

    # Check that SCH-MN-005 (ST Post-Matric) is ELIGIBLE
    st_scheme = next((s for s in data["schemes"] if s["scheme_id"] == "SCH-MN-005"), None)
    assert st_scheme is not None
    assert st_scheme["overall_outcome"] == "ELIGIBLE"
    assert st_scheme["window_status"] == "CLOSED"
    assert st_scheme["status_label"] == "Eligible by rules, window closed"
    assert st_scheme["academic_year"] == "2025-2026"
    assert st_scheme["official_source_url"] == "https://tahmanipur.gov.in"
    assert len(st_scheme["diagnostics"]) > 0

    # Check audit trail was persisted in database
    audit_stmt = select(UserEvaluation).where(UserEvaluation.session_id == "test-session-integ-1")
    audit_res = await db_session.execute(audit_stmt)
    user_eval = audit_res.scalars().first()
    assert user_eval is not None
    assert user_eval.category_evaluated == "ST"
    assert float(user_eval.income_evaluated) == 200000.0


@pytest.mark.asyncio
async def test_zero_aadhaar_rejection_and_redaction() -> None:
    """Verify 12-digit Aadhaar pattern is unconditionally rejected without leaking into errors."""
    payload = {
        "domicile_state": "MANIPUR",
        "social_category": "ST",
        "annual_family_income_inr": 200000.0,
        "course_level": "UNDERGRADUATE",
        # Explicit 12-digit Aadhaar sequence
        "session_id": "user-234567890123-session",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert response.status_code == 422
        resp_body = response.text
        # Assert raw 12-digit sequence is never reflected back
        assert "234567890123" not in resp_body
        assert "Aadhaar numbers must never be submitted" in resp_body


@pytest.mark.asyncio
async def test_validation_ranges() -> None:
    """Verify input validation caps and types."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Negative income
        res_neg = await client.post(
            "/api/v1/eligibility/evaluate",
            json={"annual_family_income_inr": -500.0},
        )
        assert res_neg.status_code == 422

        # Marks > 100
        res_marks = await client.post(
            "/api/v1/eligibility/evaluate",
            json={"marks_percent": 105.0},
        )
        assert res_marks.status_code == 422


@pytest.mark.asyncio
async def test_demo_profiles_exact_counts_and_displacement_flip(
    db_session: AsyncSession, async_client: AsyncClient
) -> None:
    """Verify demo profiles return exact counts:
    - Non-displaced: 2 Eligible / 4 Not Eligible / 0 Unknown
    - Displaced: 3 Eligible / 3 Not Eligible / 0 Unknown (SCH-MN-003 flipping on is_displaced).
    """
    await seed_pilot_schemes(db_session)

    # 1. Non-displaced profile: ST, Manipur, ₹200,000, Undergraduate, 65.0% marks
    non_displaced_payload = {
        "domicile_state": "MANIPUR",
        "social_category": "ST",
        "annual_family_income_inr": 200000.0,
        "course_level": "UNDERGRADUATE",
        "marks_percent": 65.0,
        "gender": "ANY",
        "is_displaced": False,
        "session_id": "test-demo-non-displaced",
    }
    resp1 = await async_client.post("/api/v1/eligibility/evaluate", json=non_displaced_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total_eligible"] == 2
    assert data1["total_not_eligible"] == 4
    assert data1["total_unknown"] == 0

    sch_003_non_displaced = next(s for s in data1["schemes"] if s["scheme_id"] == "SCH-MN-003")
    assert sch_003_non_displaced["overall_outcome"] == "NOT_ELIGIBLE"

    # 2. Displaced profile: identical except is_displaced = True
    displaced_payload = {
        **non_displaced_payload,
        "is_displaced": True,
        "session_id": "test-demo-displaced",
    }
    resp2 = await async_client.post("/api/v1/eligibility/evaluate", json=displaced_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total_eligible"] == 3
    assert data2["total_not_eligible"] == 3
    assert data2["total_unknown"] == 0

    sch_003_displaced = next(s for s in data2["schemes"] if s["scheme_id"] == "SCH-MN-003")
    assert sch_003_displaced["overall_outcome"] == "ELIGIBLE"
    assert sch_003_displaced["window_status"] == "CLOSED"
    assert sch_003_displaced["status_label"] == "Eligible by rules, window closed"


@pytest.mark.asyncio
async def test_evaluate_window_status_derivation_open_and_closed(
    db_session: AsyncSession, async_client: AsyncClient
) -> None:
    """Verify window_status derives from window dates (OPEN when within window, CLOSED otherwise)."""
    today = date.today()

    # 1. Register test scheme with an actively OPEN window
    open_scheme_id = f"SCH-TEST-OPEN-{uuid.uuid4().hex[:6]}"
    open_scheme = Scheme(
        scheme_id=open_scheme_id,
        official_code=f"TEST-OPEN-{uuid.uuid4().hex[:4]}",
        title_en="Actively Open Test Scholarship",
        issuing_level=SchemeLevel.STATE_SECTOR,
        ministry_or_department="Department of Testing",
        implementing_agency="Test Agency",
        canonical_source_url="https://test.gov.in",
        guidelines_document_url="https://test.gov.in/guidelines.pdf",
        is_active=True,
    )
    db_session.add(open_scheme)

    ver_id = uuid.uuid4()
    ver = SchemeVersion(
        version_id=ver_id,
        scheme_id=open_scheme_id,
        version_number=1,
        academic_year="2025-2026",
        guideline_publication_date=date(2025, 6, 1),
        content_sha256="aa" * 32,
        storage_path="documents/test_open.pdf",
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        verified_by_user_id="test_auditor",
        verification_notes="Open test fixture.",
    )
    db_session.add(ver)

    rule = SchemeEligibilityRule(
        version_id=ver_id,
        income_ceiling_annual_inr=500000.0,
        minimum_qualifying_marks_percent=50.0,
        target_categories=["ALL"],
        eligible_domiciles=["MANIPUR"],
        eligible_course_levels=["UNDERGRADUATE"],
        ast_rule_logic={"and": [{"in": [{"var": "domicile_state"}, ["MANIPUR"]]}]},
        rule_description_en="Open window test rule.",
    )
    db_session.add(rule)

    win = SchemeApplicationWindow(
        version_id=ver_id,
        portal_type=PortalType.NSP_2_0,
        portal_url="https://scholarships.gov.in",
        portal_status=PortalWindowStatus.OPEN,
        window_open_date=today - timedelta(days=5),
        window_close_date=today + timedelta(days=25),
    )
    db_session.add(win)
    await db_session.commit()

    # 2. Evaluate profile meeting this open scheme
    payload = {
        "domicile_state": "MANIPUR",
        "social_category": "GENERAL",
        "annual_family_income_inr": 300000.0,
        "course_level": "UNDERGRADUATE",
        "marks_percent": 60.0,
        "is_displaced": False,
        "session_id": "test-open-window-eval",
    }
    resp = await async_client.post("/api/v1/eligibility/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    open_res = next((s for s in data["schemes"] if s["scheme_id"] == open_scheme_id), None)
    assert open_res is not None
    assert open_res["overall_outcome"] == "ELIGIBLE"
    assert open_res["window_status"] == "OPEN"
    assert open_res["status_label"] == "Eligible, window open"
    assert any("window is OPEN" in d["explanation_en"] for d in open_res["diagnostics"])
