"""Scheme-Level Statutory Evaluator.

Coordinates scalar statutory checks and JSON-Logic AST evaluation according to
the strict 3-state deterministic outcome logic:
- ELIGIBLE: every required rule passes. Nothing failed, nothing unknown.
- NOT_ELIGIBLE: at least one required rule fails.
- UNKNOWN: no rule fails, but at least one required rule is unknown.
"""

from src.modules.catalog.domain.enums import VerificationStatus
from src.modules.catalog.domain.models import Scheme, SchemeVersion
from src.modules.eligibility.domain.ast_evaluator import evaluate_ast_node
from src.modules.eligibility.domain.enums import EvaluationOutcome, RuleOutcome
from src.modules.eligibility.domain.models import (
    RuleDiagnostic,
    SchemeEvaluationResult,
    StudentProfile,
)


def evaluate_scheme_for_student(
    scheme: Scheme, student_profile: StudentProfile
) -> SchemeEvaluationResult:
    """Evaluate a single scheme against a student profile deterministically."""
    # 1. Resolve latest version
    if not scheme.versions:
        return SchemeEvaluationResult(
            scheme_id=scheme.scheme_id,
            scheme_title=scheme.title_en,
            version_id=scheme.scheme_id,  # type: ignore[arg-type]
            overall_outcome=EvaluationOutcome.UNKNOWN,
            diagnostics=[
                RuleDiagnostic(
                    clause_name="Scheme Version Availability",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en="No version registered for this scheme.",
                    missing_fields=["scheme_version"],
                )
            ],
            missing_fields=["scheme_version"],
            ineligibility_reasons=[],
            official_source_url=scheme.canonical_source_url,
        )

    # Sort to get highest version number
    latest_version: SchemeVersion = max(scheme.versions, key=lambda v: v.version_number)

    # 2. Guard: Scheme must have verified rules
    if (
        latest_version.verification_status != VerificationStatus.OFFICIAL_VERIFIED
        or latest_version.eligibility_rule is None
    ):
        return SchemeEvaluationResult(
            scheme_id=scheme.scheme_id,
            scheme_title=scheme.title_en,
            version_id=latest_version.version_id,
            overall_outcome=EvaluationOutcome.UNKNOWN,
            diagnostics=[
                RuleDiagnostic(
                    clause_name="Statutory Verification Status",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en="Scheme does not have verified statutory eligibility rules.",
                    missing_fields=["verified_eligibility_rules"],
                )
            ],
            missing_fields=["verified_eligibility_rules"],
            ineligibility_reasons=[],
            official_source_url=scheme.canonical_source_url,
            portal_type=(
                latest_version.application_window.portal_type.value
                if latest_version.application_window
                else None
            ),
            portal_status=(
                latest_version.application_window.portal_status.value
                if latest_version.application_window
                else None
            ),
        )

    rule = latest_version.eligibility_rule
    diagnostics: list[RuleDiagnostic] = []
    missing_fields_set: list[str] = []
    ineligibility_reasons: list[str] = []

    passed_income = True
    passed_category = True
    passed_domicile = True
    passed_marks = True
    passed_course = True

    # --- Clause A: Income Ceiling Check ---
    if rule.income_ceiling_annual_inr is not None:
        ceiling = float(rule.income_ceiling_annual_inr)
        if student_profile.annual_family_income_inr is None:
            passed_income = False
            missing_fields_set.append("annual_family_income_inr")
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Income Ceiling",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en=f"Annual family income not provided (statutory ceiling: ₹{ceiling:,.2f}).",
                    missing_fields=["annual_family_income_inr"],
                )
            )
        elif student_profile.annual_family_income_inr <= ceiling:
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Income Ceiling",
                    outcome=RuleOutcome.PASS,
                    explanation_en=f"Family income (₹{student_profile.annual_family_income_inr:,.2f}) is within statutory ceiling of ₹{ceiling:,.2f}.",
                )
            )
        else:
            passed_income = False
            reason = f"Annual family income (₹{student_profile.annual_family_income_inr:,.2f}) exceeds statutory ceiling of ₹{ceiling:,.2f}."
            ineligibility_reasons.append(reason)
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Income Ceiling",
                    outcome=RuleOutcome.FAIL,
                    explanation_en=reason,
                )
            )
    else:
        diagnostics.append(
            RuleDiagnostic(
                clause_name="Income Ceiling",
                outcome=RuleOutcome.PASS,
                explanation_en="No statutory income ceiling applies to this scheme.",
            )
        )

    # --- Clause B: Social Category Check ---
    target_cats: list[str] = rule.target_categories or []
    if target_cats and "ALL" not in target_cats and "ANY" not in target_cats:
        if not student_profile.social_category:
            passed_category = False
            missing_fields_set.append("social_category")
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Social Category",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en=f"Social category not provided (eligible categories: {target_cats}).",
                    missing_fields=["social_category"],
                )
            )
        elif any(c.upper() == student_profile.social_category.upper() for c in target_cats):
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Social Category",
                    outcome=RuleOutcome.PASS,
                    explanation_en=f"Social category '{student_profile.social_category}' matches eligible categories: {target_cats}.",
                )
            )
        else:
            passed_category = False
            reason = f"Social category '{student_profile.social_category}' is not eligible (Required: {target_cats})."
            ineligibility_reasons.append(reason)
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Social Category",
                    outcome=RuleOutcome.FAIL,
                    explanation_en=reason,
                )
            )
    else:
        diagnostics.append(
            RuleDiagnostic(
                clause_name="Social Category",
                outcome=RuleOutcome.PASS,
                explanation_en="Open to all social categories.",
            )
        )

    # --- Clause C: Domicile State Check ---
    domiciles: list[str] = rule.eligible_domiciles or []
    if domiciles and "ALL_INDIA" not in domiciles and "ALL" not in domiciles:
        if not student_profile.domicile_state:
            passed_domicile = False
            missing_fields_set.append("domicile_state")
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Domicile Restriction",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en=f"Domicile state not provided (eligible domiciles: {domiciles}).",
                    missing_fields=["domicile_state"],
                )
            )
        elif any(d.upper() == student_profile.domicile_state.upper() for d in domiciles):
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Domicile Restriction",
                    outcome=RuleOutcome.PASS,
                    explanation_en=f"Domicile state '{student_profile.domicile_state}' is eligible.",
                )
            )
        else:
            passed_domicile = False
            reason = f"Domicile state '{student_profile.domicile_state}' is not eligible (Required: {domiciles})."
            ineligibility_reasons.append(reason)
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Domicile Restriction",
                    outcome=RuleOutcome.FAIL,
                    explanation_en=reason,
                )
            )
    else:
        diagnostics.append(
            RuleDiagnostic(
                clause_name="Domicile Restriction",
                outcome=RuleOutcome.PASS,
                explanation_en="Open to applicants with domicile across all Indian states.",
            )
        )

    # --- Clause D: Academic Marks Cutoff Check ---
    if rule.minimum_qualifying_marks_percent is not None:
        min_marks = float(rule.minimum_qualifying_marks_percent)
        if student_profile.marks_percent is None:
            passed_marks = False
            missing_fields_set.append("marks_percent")
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Academic Cutoff",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en=f"Qualifying marks percentage not provided (minimum required: {min_marks}%).",
                    missing_fields=["marks_percent"],
                )
            )
        elif student_profile.marks_percent >= min_marks:
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Academic Cutoff",
                    outcome=RuleOutcome.PASS,
                    explanation_en=f"Qualifying marks ({student_profile.marks_percent}%) meets or exceeds minimum threshold of {min_marks}%.",
                )
            )
        else:
            passed_marks = False
            reason = f"Qualifying marks ({student_profile.marks_percent}%) falls below minimum threshold of {min_marks}%."
            ineligibility_reasons.append(reason)
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Academic Cutoff",
                    outcome=RuleOutcome.FAIL,
                    explanation_en=reason,
                )
            )
    else:
        diagnostics.append(
            RuleDiagnostic(
                clause_name="Academic Cutoff",
                outcome=RuleOutcome.PASS,
                explanation_en="No minimum academic marks threshold required.",
            )
        )

    # --- Clause E: Course Level Check ---
    courses: list[str] = rule.eligible_course_levels or []
    if courses and "ANY" not in courses and "ALL" not in courses:
        if not student_profile.course_level:
            passed_course = False
            missing_fields_set.append("course_level")
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Course Level",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en=f"Course level not provided (eligible course levels: {courses}).",
                    missing_fields=["course_level"],
                )
            )
        elif any(c.upper() == student_profile.course_level.upper() for c in courses):
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Course Level",
                    outcome=RuleOutcome.PASS,
                    explanation_en=f"Course level '{student_profile.course_level}' is eligible.",
                )
            )
        else:
            passed_course = False
            reason = f"Course level '{student_profile.course_level}' is not eligible (Required: {courses})."
            ineligibility_reasons.append(reason)
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Course Level",
                    outcome=RuleOutcome.FAIL,
                    explanation_en=reason,
                )
            )
    else:
        diagnostics.append(
            RuleDiagnostic(
                clause_name="Course Level",
                outcome=RuleOutcome.PASS,
                explanation_en="Open to all educational course levels.",
            )
        )

    # --- Clause F: Gender Check ---
    genders: list[str] = rule.eligible_genders or ["ANY"]
    if genders and "ANY" not in genders and "ALL" not in genders:
        if not student_profile.gender:
            missing_fields_set.append("gender")
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Gender Eligibility",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en=f"Gender not provided (eligible genders: {genders}).",
                    missing_fields=["gender"],
                )
            )
        elif any(g.upper() == student_profile.gender.upper() for g in genders):
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Gender Eligibility",
                    outcome=RuleOutcome.PASS,
                    explanation_en=f"Gender '{student_profile.gender}' is eligible.",
                )
            )
        else:
            reason = f"Gender '{student_profile.gender}' is not eligible (Required: {genders})."
            ineligibility_reasons.append(reason)
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Gender Eligibility",
                    outcome=RuleOutcome.FAIL,
                    explanation_en=reason,
                )
            )

    # --- Clause G: JSON-Logic AST Evaluation ---
    if rule.ast_rule_logic:
        ast_ctx = student_profile.to_evaluation_context()
        ast_res = evaluate_ast_node(rule.ast_rule_logic, ast_ctx)
        if ast_res.outcome == RuleOutcome.PASS:
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Statutory AST Rules",
                    outcome=RuleOutcome.PASS,
                    explanation_en="All statutory logic conditions satisfied.",
                )
            )
        elif ast_res.outcome == RuleOutcome.FAIL:
            reasons_str = (
                "; ".join(ast_res.reasons)
                if ast_res.reasons
                else "Statutory AST logic condition unsatisfied."
            )
            ineligibility_reasons.append(reasons_str)
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Statutory AST Rules",
                    outcome=RuleOutcome.FAIL,
                    explanation_en=reasons_str,
                )
            )
        else:  # UNKNOWN
            for mf in ast_res.missing_fields:
                if mf not in missing_fields_set:
                    missing_fields_set.append(mf)
            err_msg = (
                ast_res.error or f"Missing required information: {list(ast_res.missing_fields)}"
            )
            diagnostics.append(
                RuleDiagnostic(
                    clause_name="Statutory AST Rules",
                    outcome=RuleOutcome.UNKNOWN,
                    explanation_en=f"Cannot evaluate statutory AST rule: {err_msg}",
                    missing_fields=list(ast_res.missing_fields),
                )
            )

    # 4. Strict Overall Outcome Invariant
    # ELIGIBLE: every required rule passes. Nothing failed, nothing unknown.
    # NOT_ELIGIBLE: at least one required rule fails.
    # UNKNOWN: no rule fails, but at least one required rule is unknown.
    has_failure = any(d.outcome == RuleOutcome.FAIL for d in diagnostics)
    has_unknown = any(d.outcome == RuleOutcome.UNKNOWN for d in diagnostics)

    if has_failure:
        overall_outcome = EvaluationOutcome.NOT_ELIGIBLE
    elif has_unknown:
        overall_outcome = EvaluationOutcome.UNKNOWN
    else:
        overall_outcome = EvaluationOutcome.ELIGIBLE

    # Portal details
    window = latest_version.application_window
    portal_type_val = window.portal_type.value if window else None
    portal_status_val = window.portal_status.value if window else None

    return SchemeEvaluationResult(
        scheme_id=scheme.scheme_id,
        scheme_title=scheme.title_en,
        version_id=latest_version.version_id,
        overall_outcome=overall_outcome,
        diagnostics=diagnostics,
        missing_fields=missing_fields_set,
        ineligibility_reasons=ineligibility_reasons,
        official_source_url=scheme.canonical_source_url,
        portal_type=portal_type_val,
        portal_status=portal_status_val,
        passed_income_check=passed_income,
        passed_category_check=passed_category,
        passed_domicile_check=passed_domicile,
        passed_marks_check=passed_marks,
        passed_course_check=passed_course,
    )
