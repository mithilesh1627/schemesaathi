"""Golden Persona Test Suite: 20 Student Profiles for Deterministic Verification.

Invariant:
    FALSE POSITIVE COUNT MUST BE EXACTLY ZERO.
    No student profile may evaluate to ELIGIBLE unless every statutory criterion
    genuinely passes.

Coverage:
- 5 Clearly Eligible personas across seeded Manipur schemes
- 6 Single-failure personas testing every distinct rule type (income, category, domicile, marks, course, displacement)
- 4 Missing-field personas testing UNKNOWN outcome handling
- 3 Boundary-value personas testing exact equality and ceiling + 1
- 1 Pan-India guardrail persona testing non-Manipur domicile (Karnataka)
- 1 Unverified scheme guardrail persona testing that unverified rules return UNKNOWN
"""

import uuid
from dataclasses import dataclass
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.enums import (
    DocumentLifecycleState,
    SchemeLevel,
    VerificationStatus,
)
from src.modules.catalog.domain.models import (
    Scheme,
    SchemeEligibilityRule,
    SchemeVersion,
)
from src.modules.catalog.infrastructure.seed_data import seed_pilot_schemes
from src.modules.eligibility.domain.enums import EvaluationOutcome
from src.modules.eligibility.domain.models import StudentProfile
from src.modules.eligibility.domain.scheme_evaluator import evaluate_scheme_for_student


@dataclass
class GoldenPersonaFixture:
    persona_id: str
    description: str
    target_scheme_id: str
    profile: StudentProfile
    expected_outcome: EvaluationOutcome
    expected_failing_clause: str | None = None
    expected_missing_field: str | None = None


def _create_pan_india_fixture_scheme() -> Scheme:
    """Non-Manipur state-agnostic test fixture (Karnataka SC Post-Matric)."""
    scheme = Scheme(
        scheme_id="SCH-TEST-KA-001",
        official_code="KA-SC-POST",
        title_en="Karnataka Post-Matric Scholarship for SC Students",
        title_hi="कर्नाटक अनुसूचित जाति मैट्रिक-उपरांत छात्रवृत्ति",
        title_mni_beng="ꯀꯔꯅꯥꯇꯀꯥ ꯑꯦꯁ.ꯁꯤ. ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ",
        title_mni_latn="Karnataka Post-Matric Scholarship for SC Students",
        issuing_level=SchemeLevel.STATE_SECTOR,
        ministry_or_department="Social Welfare Department, Government of Karnataka",
        implementing_agency="Karnataka Social Welfare Department",
        canonical_source_url="https://ssp.postmatric.karnataka.gov.in",
        guidelines_document_url="https://ssp.postmatric.karnataka.gov.in/guidelines.pdf",
        is_active=True,
    )
    version = SchemeVersion(
        version_id=uuid.uuid4(),
        scheme_id=scheme.scheme_id,
        version_number=1,
        academic_year="2024-2025",
        guideline_publication_date=date(2024, 1, 1),
        content_sha256="test-ka-sc-sha256",
        lifecycle_state=DocumentLifecycleState.STORED.value,
        verification_status=VerificationStatus.OFFICIAL_VERIFIED,
        verified_by_user_id="test-auditor",
        verification_notes="State-agnostic pan-India guardrail test fixture.",
    )
    scheme.versions = [version]
    rule = SchemeEligibilityRule(
        rule_id=uuid.uuid4(),
        version_id=version.version_id,
        income_ceiling_annual_inr=250000.00,
        minimum_qualifying_marks_percent=None,
        target_categories=["SC"],
        eligible_domiciles=["KARNATAKA"],
        eligible_course_levels=["UNDERGRADUATE"],
        eligible_genders=["ANY"],
        ast_rule_logic={
            "and": [
                {"<=": [{"var": "annual_family_income_inr"}, 250000]},
                {"in": [{"var": "social_category"}, ["SC"]]},
                {"in": [{"var": "domicile_state"}, ["KARNATAKA"]]},
                {"in": [{"var": "course_level"}, ["UNDERGRADUATE"]]},
            ]
        },
        rule_description_en="Income <= 2.5L, Category SC, Domicile Karnataka, Course UG.",
    )
    version.eligibility_rule = rule
    return scheme


def _create_unverified_fixture_scheme() -> Scheme:
    """Scheme fixture with provisional / unverified status."""
    scheme = Scheme(
        scheme_id="SCH-TEST-UNVERIFIED-001",
        official_code="PROVISIONAL-SCHEME",
        title_en="Provisional Unverified Scholarship",
        title_hi="अनंतिम छात्रवृत्ति",
        title_mni_beng="ꯄ꯭ꯔꯣꯚꯤꯖꯅꯦꯜ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ",
        title_mni_latn="Provisional Unverified Scholarship",
        issuing_level=SchemeLevel.CENTRAL_SECTOR,
        ministry_or_department="Provisional Dept",
        implementing_agency="Provisional Agency",
        canonical_source_url="https://provisional.gov.in",
        guidelines_document_url="https://provisional.gov.in/guidelines.pdf",
        is_active=True,
    )
    version = SchemeVersion(
        version_id=uuid.uuid4(),
        scheme_id=scheme.scheme_id,
        version_number=1,
        academic_year="2024-2025",
        content_sha256="provisional-sha256",
        lifecycle_state=DocumentLifecycleState.RECEIVED.value,
        verification_status=VerificationStatus.OFFICIAL_PROVISIONAL,  # NOT OFFICIAL_VERIFIED
    )
    scheme.versions = [version]
    return scheme


# Define the exact 20 golden personas
GOLDEN_PERSONAS: list[GoldenPersonaFixture] = [
    # --- Group 1: 5 Clearly Eligible Personas ---
    GoldenPersonaFixture(
        persona_id="GP-01",
        description="ST Undergraduate Student eligible for Post-Matric ST",
        target_scheme_id="SCH-MN-005",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="UNDERGRADUATE",
            marks_percent=70.0,
            gender="FEMALE",
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    GoldenPersonaFixture(
        persona_id="GP-02",
        description="OBC Undergraduate Student eligible for Post-Matric OBC",
        target_scheme_id="SCH-MN-007",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="OBC",
            annual_family_income_inr=180000.0,
            course_level="UNDERGRADUATE",
            marks_percent=75.0,
            gender="MALE",
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    GoldenPersonaFixture(
        persona_id="GP-03",
        description="SC Undergraduate Student eligible for Post-Matric SC",
        target_scheme_id="SCH-MN-009",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="SC",
            annual_family_income_inr=120000.0,
            course_level="UNDERGRADUATE",
            marks_percent=62.0,
            gender="FEMALE",
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    GoldenPersonaFixture(
        persona_id="GP-04",
        description="ST Class 10 Student eligible for Pre-Matric ST",
        target_scheme_id="SCH-MN-006",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=200000.0,
            course_level="CLASS_9_10",
            marks_percent=65.0,
            gender="MALE",
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    GoldenPersonaFixture(
        persona_id="GP-05",
        description="Conflict Displaced Student eligible for CMCSRS",
        target_scheme_id="SCH-MN-003",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",
            annual_family_income_inr=500000.0,
            course_level="UNDERGRADUATE",
            marks_percent=55.0,
            is_displaced=True,
            gender="FEMALE",
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    # --- Group 2: 6 Single-Failure Personas (Testing Each Distinct Rule) ---
    GoldenPersonaFixture(
        persona_id="GP-06",
        description="Income exceeds ₹2.5L ceiling for ST Post-Matric",
        target_scheme_id="SCH-MN-005",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=280000.0,  # Exceeds 250,000
            course_level="UNDERGRADUATE",
            marks_percent=55.0,
        ),
        expected_outcome=EvaluationOutcome.NOT_ELIGIBLE,
        expected_failing_clause="Income Ceiling",
    ),
    GoldenPersonaFixture(
        persona_id="GP-07",
        description="Wrong Category (General instead of ST) for ST Post-Matric",
        target_scheme_id="SCH-MN-005",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",  # Not ST
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=55.0,
        ),
        expected_outcome=EvaluationOutcome.NOT_ELIGIBLE,
        expected_failing_clause="Social Category",
    ),
    GoldenPersonaFixture(
        persona_id="GP-08",
        description="Wrong Domicile (Assam instead of Manipur) for State Merit",
        target_scheme_id="SCH-MN-001",
        profile=StudentProfile(
            domicile_state="ASSAM",  # Not Manipur
            social_category="GENERAL",
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=85.0,
        ),
        expected_outcome=EvaluationOutcome.NOT_ELIGIBLE,
        expected_failing_clause="Domicile Restriction",
    ),
    GoldenPersonaFixture(
        persona_id="GP-09",
        description="Marks 58.5% below 60% cutoff for State Merit",
        target_scheme_id="SCH-MN-001",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=58.5,  # Below 60%
        ),
        expected_outcome=EvaluationOutcome.NOT_ELIGIBLE,
        expected_failing_clause="Academic Cutoff",
    ),
    GoldenPersonaFixture(
        persona_id="GP-10",
        description="Course Level PG instead of Class 9-10 for Pre-Matric ST",
        target_scheme_id="SCH-MN-006",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="POSTGRADUATE",  # Not Class 9-10
            marks_percent=70.0,
        ),
        expected_outcome=EvaluationOutcome.NOT_ELIGIBLE,
        expected_failing_clause="Course Level",
    ),
    GoldenPersonaFixture(
        persona_id="GP-11",
        description="Not Displaced for CMCSRS Rehabilitation Scheme",
        target_scheme_id="SCH-MN-003",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",
            annual_family_income_inr=400000.0,
            course_level="UNDERGRADUATE",
            is_displaced=False,  # Not displaced
        ),
        expected_outcome=EvaluationOutcome.NOT_ELIGIBLE,
        expected_failing_clause="Statutory AST Rules",
    ),
    # --- Group 3: 4 Missing-Field Personas (Testing UNKNOWN Outcome) ---
    GoldenPersonaFixture(
        persona_id="GP-12",
        description="Missing Income for State Merit returns UNKNOWN",
        target_scheme_id="SCH-MN-001",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",
            annual_family_income_inr=None,  # Missing
            course_level="UNDERGRADUATE",
            marks_percent=75.0,
        ),
        expected_outcome=EvaluationOutcome.UNKNOWN,
        expected_missing_field="annual_family_income_inr",
    ),
    GoldenPersonaFixture(
        persona_id="GP-13",
        description="Missing Social Category for ST Post-Matric returns UNKNOWN",
        target_scheme_id="SCH-MN-005",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category=None,  # Missing
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=70.0,
        ),
        expected_outcome=EvaluationOutcome.UNKNOWN,
        expected_missing_field="social_category",
    ),
    GoldenPersonaFixture(
        persona_id="GP-14",
        description="Missing Domicile State returns UNKNOWN",
        target_scheme_id="SCH-MN-005",
        profile=StudentProfile(
            domicile_state=None,  # Missing
            social_category="ST",
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=70.0,
        ),
        expected_outcome=EvaluationOutcome.UNKNOWN,
        expected_missing_field="domicile_state",
    ),
    GoldenPersonaFixture(
        persona_id="GP-15",
        description="Missing Marks Percent for State Merit returns UNKNOWN",
        target_scheme_id="SCH-MN-001",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",
            annual_family_income_inr=300000.0,
            course_level="UNDERGRADUATE",
            marks_percent=None,  # Missing
        ),
        expected_outcome=EvaluationOutcome.UNKNOWN,
        expected_missing_field="marks_percent",
    ),
    # --- Group 4: 3 Boundary-Value Personas ---
    GoldenPersonaFixture(
        persona_id="GP-16",
        description="Income Exactly at Ceiling (₹2,50,000.00) passes boundary check",
        target_scheme_id="SCH-MN-005",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=250000.0,  # Exact ceiling
            course_level="UNDERGRADUATE",
            marks_percent=55.0,
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    GoldenPersonaFixture(
        persona_id="GP-17",
        description="Income Ceiling + 1 Rupee (₹2,50,001.00) fails boundary check",
        target_scheme_id="SCH-MN-005",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=250001.0,  # Ceiling + 1 INR
            course_level="UNDERGRADUATE",
            marks_percent=55.0,
        ),
        expected_outcome=EvaluationOutcome.NOT_ELIGIBLE,
        expected_failing_clause="Income Ceiling",
    ),
    GoldenPersonaFixture(
        persona_id="GP-18",
        description="Marks Exactly at Cutoff (60.0%) and Income at Ceiling passes",
        target_scheme_id="SCH-MN-001",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",
            annual_family_income_inr=450000.0,  # Exact ceiling
            course_level="UNDERGRADUATE",
            marks_percent=60.0,  # Exact cutoff
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    # --- Group 5: 1 Pan-India Guardrail Persona (Non-Manipur Domicile) ---
    GoldenPersonaFixture(
        persona_id="GP-19",
        description="Karnataka SC Student eligible for Karnataka State Scheme",
        target_scheme_id="SCH-TEST-KA-001",
        profile=StudentProfile(
            domicile_state="KARNATAKA",
            social_category="SC",
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=70.0,
        ),
        expected_outcome=EvaluationOutcome.ELIGIBLE,
    ),
    # --- Group 6: 1 Unverified Scheme Guardrail Persona ---
    GoldenPersonaFixture(
        persona_id="GP-20",
        description="Scheme with unverified rules returns UNKNOWN, never ELIGIBLE",
        target_scheme_id="SCH-TEST-UNVERIFIED-001",
        profile=StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=100000.0,
            course_level="UNDERGRADUATE",
            marks_percent=80.0,
        ),
        expected_outcome=EvaluationOutcome.UNKNOWN,
        expected_missing_field="verified_eligibility_rules",
    ),
]


@pytest.mark.asyncio
async def test_twenty_golden_personas_zero_false_positives(db_session: AsyncSession) -> None:
    """Execute all 20 golden personas and assert 0 false positives."""
    # Seed the pilot schemes into session
    await seed_pilot_schemes(db_session)

    # Build scheme map including test fixtures
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = select(Scheme).options(
        selectinload(Scheme.versions).selectinload(SchemeVersion.eligibility_rule),
        selectinload(Scheme.versions).selectinload(SchemeVersion.application_window),
    )
    res = await db_session.execute(stmt)
    schemes_dict: dict[str, Scheme] = {s.scheme_id: s for s in res.scalars().all()}

    # Add external fixtures
    schemes_dict["SCH-TEST-KA-001"] = _create_pan_india_fixture_scheme()
    schemes_dict["SCH-TEST-UNVERIFIED-001"] = _create_unverified_fixture_scheme()

    false_positive_count = 0
    evaluation_logs: list[str] = []

    assert len(GOLDEN_PERSONAS) == 20, f"Expected 20 golden personas, got {len(GOLDEN_PERSONAS)}"

    for persona in GOLDEN_PERSONAS:
        scheme = schemes_dict.get(persona.target_scheme_id)
        assert scheme is not None, (
            f"Scheme {persona.target_scheme_id} not found for {persona.persona_id}"
        )

        result = evaluate_scheme_for_student(scheme, persona.profile)

        # Check for False Positive:
        # A false positive occurs if the profile is NOT expected to be eligible, but evaluated to ELIGIBLE!
        if (
            persona.expected_outcome != EvaluationOutcome.ELIGIBLE
            and result.overall_outcome == EvaluationOutcome.ELIGIBLE
        ):
            false_positive_count += 1
            evaluation_logs.append(
                f"FALSE POSITIVE in {persona.persona_id} ({persona.description}): "
                f"expected {persona.expected_outcome}, got {result.overall_outcome}"
            )

        # Verify exact outcome match
        assert result.overall_outcome == persona.expected_outcome, (
            f"Persona {persona.persona_id} mismatch: expected {persona.expected_outcome}, "
            f"got {result.overall_outcome}. Ineligibility reasons: {result.ineligibility_reasons}, "
            f"Missing fields: {result.missing_fields}"
        )

        # Verify expected failing clause if specified
        if persona.expected_failing_clause:
            assert any(
                d.clause_name == persona.expected_failing_clause and d.outcome.value == "FAIL"
                for d in result.diagnostics
            ), (
                f"Persona {persona.persona_id} did not fail expected clause '{persona.expected_failing_clause}'"
            )

        # Verify expected missing field if specified
        if persona.expected_missing_field:
            assert persona.expected_missing_field in result.missing_fields, (
                f"Persona {persona.persona_id} did not report missing field '{persona.expected_missing_field}'"
            )

    # Hard Invariant: 0 False Positives
    assert false_positive_count == 0, f"False positives detected: {evaluation_logs}"
