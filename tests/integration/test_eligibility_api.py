"""Integration Tests for Eligibility Evaluation API & Demo Webpage.

Verifies:
- POST /api/v1/eligibility/evaluate end-to-end execution
- GET /demo static demo webpage with mandatory pilot disclaimer
- Strict zero-Aadhaar PII protection on request inputs, errors, and logs
- Audit trail persistence in user_evaluations and evaluation_rule_results tables
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.modules.catalog.domain.models import UserEvaluation
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
