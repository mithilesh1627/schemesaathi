"""Pydantic API Request and Response Schemas for Eligibility Evaluation."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.security import AADHAAR_PATTERN, sanitize_sensitive_data
from src.modules.eligibility.domain.enums import EvaluationOutcome, RuleOutcome


class StudentProfileRequest(BaseModel):
    """Student profile attributes submitted for statutory eligibility evaluation."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    domicile_state: str | None = Field(
        default=None,
        description="State of permanent domicile (e.g. MANIPUR, ASSAM, KARNATAKA)",
        examples=["MANIPUR"],
    )
    social_category: str | None = Field(
        default=None,
        description="Social / caste reservation category (GENERAL, SC, ST, OBC, EBC)",
        examples=["ST"],
    )
    annual_family_income_inr: float | None = Field(
        default=None,
        description="Total annual family income from all sources in Indian Rupees",
        examples=[200000.0],
        ge=0,
    )
    course_level: str | None = Field(
        default=None,
        description="Educational course level (UNDERGRADUATE, POSTGRADUATE, CLASS_9_10, POST_MATRIC, DIPLOMA)",
        examples=["UNDERGRADUATE"],
    )
    marks_percent: float | None = Field(
        default=None,
        description="Aggregate marks percentage in previous qualifying exam",
        examples=[65.5],
        ge=0.0,
        le=100.0,
    )
    gender: str | None = Field(
        default=None,
        description="Gender identity (MALE, FEMALE, TRANSGENDER, OTHER)",
        examples=["FEMALE"],
    )
    is_disability: bool = Field(
        default=False,
        description="Whether applicant possesses a certified benchmark disability (>=40%)",
    )
    is_displaced: bool = Field(
        default=False,
        description="Whether applicant is displaced or affected by social conflict (e.g., Manipur unrest)",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional client session identifier for telemetry and audit tracing",
    )

    @model_validator(mode="before")
    @classmethod
    def sanitize_and_check_pii(cls, data: Any) -> Any:
        """Sanitize any prospective 12-digit sequence before validation to prevent log leakage."""
        if isinstance(data, dict):
            # Check for direct 12-digit Aadhaar input
            for _field_name, value in data.items():
                if isinstance(value, str):
                    digits = re.sub(r"\D", "", value)
                    if len(digits) == 12 or AADHAAR_PATTERN.search(value):
                        raise ValueError(
                            "Aadhaar numbers must never be submitted. SchemeSaathi operates under "
                            "a strict Zero-Aadhaar policy compliant with the DPDP Act 2023."
                        )
            return sanitize_sensitive_data(data)
        return data


class RuleDiagnosticResponse(BaseModel):
    """Per-clause evaluation diagnostic with plain-language explanation."""

    model_config = ConfigDict(from_attributes=True)

    clause_name: str
    outcome: RuleOutcome
    explanation_en: str
    missing_fields: list[str] = Field(default_factory=list)


class SchemeEvaluationResponse(BaseModel):
    """Evaluated scheme with deterministic outcome, plain-language diagnostics, and portal links."""

    model_config = ConfigDict(from_attributes=True)

    scheme_id: str
    scheme_title: str
    overall_outcome: EvaluationOutcome
    diagnostics: list[RuleDiagnosticResponse]
    missing_fields: list[str]
    ineligibility_reasons: list[str]
    official_source_url: str
    portal_type: str | None = None
    portal_status: str | None = None


class BatchEvaluationResponse(BaseModel):
    """Aggregate evaluation response containing all evaluated schemes and audit metrics."""

    model_config = ConfigDict(from_attributes=True)

    total_schemes_checked: int
    total_eligible: int
    total_not_eligible: int
    total_unknown: int
    execution_duration_ms: int
    schemes: list[SchemeEvaluationResponse]
