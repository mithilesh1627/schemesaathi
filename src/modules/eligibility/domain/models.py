"""Domain Models for Student Profiles and Evaluation Results."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.eligibility.domain.enums import EvaluationOutcome, RuleOutcome


@dataclass
class StudentProfile:
    """Domain representation of a citizen/student seeking scheme eligibility."""

    domicile_state: str | None = None
    social_category: str | None = None
    annual_family_income_inr: float | None = None
    course_level: str | None = None
    marks_percent: float | None = None
    gender: str | None = None
    is_disability: bool = False
    is_displaced: bool = False
    session_id: str | None = None
    extra_attributes: dict[str, Any] = field(default_factory=dict)

    def to_evaluation_context(self) -> dict[str, Any]:
        """Convert profile into evaluation context for AST evaluation."""
        ctx: dict[str, Any] = {
            "domicile_state": self.domicile_state,
            "social_category": self.social_category,
            "annual_family_income_inr": self.annual_family_income_inr,
            "course_level": self.course_level,
            "marks_percent": self.marks_percent,
            "gender": self.gender,
            "is_disability": self.is_disability,
            "is_displaced": self.is_displaced,
        }
        ctx.update(self.extra_attributes)
        return ctx


@dataclass
class RuleDiagnostic:
    """Diagnostic detail for an individual statutory criteria check."""

    clause_name: str
    outcome: RuleOutcome
    explanation_en: str
    missing_fields: list[str] = field(default_factory=list)


@dataclass
class SchemeEvaluationResult:
    """Detailed scheme evaluation outcome with per-rule diagnostics and audit trails."""

    scheme_id: str
    scheme_title: str
    version_id: uuid.UUID
    overall_outcome: EvaluationOutcome
    diagnostics: list[RuleDiagnostic]
    missing_fields: list[str]
    ineligibility_reasons: list[str]
    official_source_url: str
    portal_type: str | None = None
    portal_status: str | None = None
    passed_income_check: bool = False
    passed_category_check: bool = False
    passed_domicile_check: bool = False
    passed_marks_check: bool = False
    passed_course_check: bool = False
