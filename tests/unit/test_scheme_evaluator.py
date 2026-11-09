"""Unit Tests for Scheme-Level Statutory Evaluator.

Verifies:
- Strict 3-state outcome logic: ELIGIBLE, NOT_ELIGIBLE, UNKNOWN
- Unverified rule or missing rule -> UNKNOWN
- Exact clause failures and plain-language explanation generation
- Correct accumulation of missing criteria fields
"""

import uuid
from datetime import date, timedelta
from typing import Any

from src.modules.catalog.domain.enums import (
    DocumentLifecycleState,
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
from src.modules.eligibility.domain.enums import EvaluationOutcome, RuleOutcome
from src.modules.eligibility.domain.models import StudentProfile
from src.modules.eligibility.domain.scheme_evaluator import evaluate_scheme_for_student


def _build_test_scheme(
    verification_status: VerificationStatus = VerificationStatus.OFFICIAL_VERIFIED,
    income_ceiling: float | None = 250000.0,
    target_categories: list[str] | None = None,
    eligible_domiciles: list[str] | None = None,
    minimum_marks: float | None = None,
    eligible_courses: list[str] | None = None,
    has_rule: bool = True,
    ast_logic: dict[str, Any] | None = None,
    academic_year: str = "2025-2026",
    window_open_date: date | None = None,
    window_close_date: date | None = None,
    portal_status: PortalWindowStatus = PortalWindowStatus.CLOSED,
) -> Scheme:
    """Helper to build in-memory Scheme objects for testing."""
    if target_categories is None:
        target_categories = ["ST"]
    if eligible_domiciles is None:
        eligible_domiciles = ["MANIPUR"]
    if eligible_courses is None:
        eligible_courses = ["UNDERGRADUATE"]

    scheme = Scheme(
        scheme_id="SCH-TEST-001",
        official_code="TEST-SCHEME",
        title_en="Test Scholarship Scheme",
        title_hi="परीक्षण छात्रवृत्ति",
        title_mni_beng="ꯇꯦꯁ꯭ꯠ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ",
        title_mni_latn="Test Scholarship Scheme",
        issuing_level=SchemeLevel.STATE_SECTOR,
        ministry_or_department="Test Department",
        implementing_agency="Test Agency",
        canonical_source_url="https://test.gov.in/scholarship",
        guidelines_document_url="https://test.gov.in/guidelines.pdf",
        is_active=True,
    )

    version = SchemeVersion(
        version_id=uuid.uuid4(),
        scheme_id=scheme.scheme_id,
        version_number=1,
        academic_year=academic_year,
        guideline_publication_date=date(2025, 1, 1),
        content_sha256="test-sha256-hash",
        lifecycle_state=DocumentLifecycleState.STORED.value,
        verification_status=verification_status,
        verified_by_user_id="test-auditor",
        verification_notes="Verified for unit testing.",
    )
    scheme.versions = [version]

    if has_rule:
        rule = SchemeEligibilityRule(
            rule_id=uuid.uuid4(),
            version_id=version.version_id,
            income_ceiling_annual_inr=income_ceiling,
            minimum_qualifying_marks_percent=minimum_marks,
            target_categories=target_categories,
            eligible_domiciles=eligible_domiciles,
            eligible_course_levels=eligible_courses,
            eligible_genders=["ANY"],
            ast_rule_logic=ast_logic or {},
            rule_description_en="Test rule description.",
        )
        version.eligibility_rule = rule

    window = SchemeApplicationWindow(
        window_id=uuid.uuid4(),
        version_id=version.version_id,
        portal_type=PortalType.NSP_2_0,
        portal_url="https://scholarships.gov.in",
        portal_status=portal_status,
        window_open_date=window_open_date,
        window_close_date=window_close_date,
    )
    version.application_window = window

    return scheme


class TestSchemeEvaluatorOutcomes:
    """Tests for scheme evaluation outcomes and invariants."""

    def test_unverified_scheme_returns_unknown(self) -> None:
        scheme = _build_test_scheme(verification_status=VerificationStatus.OFFICIAL_PROVISIONAL)
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.UNKNOWN
        assert "verified_eligibility_rules" in res.missing_fields

    def test_missing_eligibility_rule_returns_unknown(self) -> None:
        scheme = _build_test_scheme(has_rule=False)
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.UNKNOWN

    def test_all_criteria_met_returns_eligible(self) -> None:
        scheme = _build_test_scheme(
            income_ceiling=250000.0,
            target_categories=["ST"],
            eligible_domiciles=["MANIPUR"],
            eligible_courses=["UNDERGRADUATE"],
            minimum_marks=60.0,
        )
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=65.0,
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.ELIGIBLE
        assert res.passed_income_check is True
        assert res.passed_category_check is True
        assert res.passed_domicile_check is True
        assert res.passed_marks_check is True
        assert res.passed_course_check is True
        assert len(res.ineligibility_reasons) == 0
        assert len(res.missing_fields) == 0

    def test_single_failure_income_returns_not_eligible(self) -> None:
        scheme = _build_test_scheme(income_ceiling=250000.0)
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=300000.0,  # Exceeds 250000
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.NOT_ELIGIBLE
        assert res.passed_income_check is False
        assert any("exceeds statutory ceiling" in r for r in res.ineligibility_reasons)

    def test_single_failure_category_returns_not_eligible(self) -> None:
        scheme = _build_test_scheme(target_categories=["ST"])
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="GENERAL",  # Not ST
            annual_family_income_inr=100000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.NOT_ELIGIBLE
        assert res.passed_category_check is False

    def test_single_failure_domicile_returns_not_eligible(self) -> None:
        scheme = _build_test_scheme(eligible_domiciles=["MANIPUR"])
        profile = StudentProfile(
            domicile_state="ASSAM",  # Not Manipur
            social_category="ST",
            annual_family_income_inr=100000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.NOT_ELIGIBLE
        assert res.passed_domicile_check is False

    def test_single_failure_marks_returns_not_eligible(self) -> None:
        scheme = _build_test_scheme(minimum_marks=60.0)
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=100000.0,
            course_level="UNDERGRADUATE",
            marks_percent=55.0,  # Below 60.0%
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.NOT_ELIGIBLE
        assert res.passed_marks_check is False

    def test_missing_field_returns_unknown_when_no_failures(self) -> None:
        scheme = _build_test_scheme(income_ceiling=250000.0, minimum_marks=60.0)
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=200000.0,
            course_level="UNDERGRADUATE",
            marks_percent=None,  # Missing marks
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.UNKNOWN
        assert "marks_percent" in res.missing_fields

    def test_failure_overrides_unknown(self) -> None:
        # If income fails, but marks are unknown, overall outcome must be NOT_ELIGIBLE
        scheme = _build_test_scheme(income_ceiling=250000.0, minimum_marks=60.0)
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=400000.0,  # Fails income
            course_level="UNDERGRADUATE",
            marks_percent=None,  # Unknown marks
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.NOT_ELIGIBLE
        assert res.passed_income_check is False

    def test_window_status_closed_derived_from_dates_even_if_portal_status_open(self) -> None:
        """Requirement: Window status derived from dates, never copied from portal_status alone."""
        today = date.today()
        # Scheme window closed yesterday, but portal_status is OPEN
        scheme = _build_test_scheme(
            portal_status=PortalWindowStatus.OPEN,
            window_open_date=today - timedelta(days=60),
            window_close_date=today - timedelta(days=1),
        )
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.ELIGIBLE
        assert res.portal_status == "OPEN"
        assert res.window_status == "CLOSED"
        assert res.status_label == "Eligible by rules, window closed"
        assert any("window is CLOSED" in d.explanation_en for d in res.diagnostics)
        win_diag = next(d for d in res.diagnostics if d.clause_name == "Application Window Status")
        assert win_diag.outcome == RuleOutcome.FAIL

    def test_window_status_open_when_today_is_inside_window(self) -> None:
        """Requirement: Window status is OPEN when today is inside statutory window."""
        today = date.today()
        scheme = _build_test_scheme(
            portal_status=PortalWindowStatus.OPEN,
            window_open_date=today - timedelta(days=10),
            window_close_date=today + timedelta(days=20),
        )
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.ELIGIBLE
        assert res.window_status == "OPEN"
        assert res.status_label == "Eligible, window open"
        assert any("window is OPEN" in d.explanation_en for d in res.diagnostics)
        win_diag = next(d for d in res.diagnostics if d.clause_name == "Application Window Status")
        assert win_diag.outcome == RuleOutcome.PASS

    def test_window_status_closed_when_window_dates_are_none(self) -> None:
        """When window dates are missing, window_status safely defaults to CLOSED."""
        scheme = _build_test_scheme(
            window_open_date=None,
            window_close_date=None,
        )
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.ELIGIBLE
        assert res.window_status == "CLOSED"
        assert res.status_label == "Eligible by rules, window closed"
        win_diag = next(d for d in res.diagnostics if d.clause_name == "Application Window Status")
        assert win_diag.outcome == RuleOutcome.FAIL

    def test_window_status_open_on_unknown_outcome(self) -> None:
        """D4 Regression: Unknown outcome with open window derives window_status: OPEN and PASS diagnostic."""
        today = date.today()
        scheme = _build_test_scheme(
            verification_status=VerificationStatus.OFFICIAL_PROVISIONAL,
            window_open_date=today - timedelta(days=5),
            window_close_date=today + timedelta(days=20),
            portal_status=PortalWindowStatus.OPEN,
        )
        profile = StudentProfile(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=150000.0,
            course_level="UNDERGRADUATE",
        )
        res = evaluate_scheme_for_student(scheme, profile)
        assert res.overall_outcome == EvaluationOutcome.UNKNOWN
        assert res.window_status == "OPEN"
        assert res.status_label == "Conditionally eligible / information missing"
        win_diag = next(d for d in res.diagnostics if d.clause_name == "Application Window Status")
        assert win_diag.outcome == RuleOutcome.PASS
        assert "window is OPEN" in win_diag.explanation_en
