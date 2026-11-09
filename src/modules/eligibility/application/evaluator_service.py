"""Application Service for Deterministic Scheme Eligibility Evaluation."""

import time
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.modules.catalog.domain.enums import EvaluationStatus
from src.modules.catalog.domain.models import (
    EvaluationRuleResult,
    Scheme,
    SchemeVersion,
    UserEvaluation,
)
from src.modules.eligibility.application.schemas import (
    BatchEvaluationResponse,
    RuleDiagnosticResponse,
    SchemeEvaluationResponse,
    StudentProfileRequest,
)
from src.modules.eligibility.domain.enums import EvaluationOutcome
from src.modules.eligibility.domain.models import SchemeEvaluationResult, StudentProfile
from src.modules.eligibility.domain.scheme_evaluator import evaluate_scheme_for_student

logger = get_logger(__name__)


class EligibilityEvaluatorService:
    """Orchestrates deterministic statutory scheme evaluations and audit trail persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def evaluate_student_profile(
        self, request: StudentProfileRequest, persist_audit: bool = True
    ) -> BatchEvaluationResponse:
        """Evaluate student profile against all active schemes and persist audit log."""
        start_time = time.perf_counter()

        profile = StudentProfile(
            domicile_state=request.domicile_state,
            social_category=request.social_category,
            annual_family_income_inr=request.annual_family_income_inr,
            course_level=request.course_level,
            marks_percent=request.marks_percent,
            gender=request.gender,
            is_disability=request.is_disability,
            is_displaced=request.is_displaced,
            session_id=request.session_id,
        )

        # 1. Fetch active schemes with versions, rules, and windows
        stmt = (
            select(Scheme)
            .where(Scheme.is_active == True)  # noqa: E712
            .options(
                selectinload(Scheme.versions).selectinload(SchemeVersion.eligibility_rule),
                selectinload(Scheme.versions).selectinload(SchemeVersion.application_window),
            )
            .order_by(Scheme.title_en.asc())
        )
        res = await self.session.execute(stmt)
        schemes: Sequence[Scheme] = res.scalars().all()

        # 2. Evaluate deterministically
        evaluation_results: list[SchemeEvaluationResult] = []
        for scheme in schemes:
            eval_res = evaluate_scheme_for_student(scheme, profile)
            evaluation_results.append(eval_res)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # 3. Persist audit trail to PostgreSQL if requested and schemes were evaluated
        if persist_audit and evaluation_results:
            try:
                session_id = request.session_id or f"sess_{uuid.uuid4().hex[:16]}"
                income_val = (
                    request.annual_family_income_inr
                    if request.annual_family_income_inr is not None
                    else -1.0
                )

                user_eval = UserEvaluation(
                    evaluation_id=uuid.uuid4(),
                    session_id=session_id,
                    category_evaluated=request.social_category or "NOT_PROVIDED",
                    income_evaluated=income_val,
                    domicile_evaluated=request.domicile_state or "NOT_PROVIDED",
                    course_level_evaluated=request.course_level or "NOT_PROVIDED",
                    marks_percent_evaluated=request.marks_percent,
                    gender_evaluated=request.gender,
                    is_disability_evaluated=request.is_disability,
                    is_displaced_affected=request.is_displaced,
                    total_schemes_checked=len(evaluation_results),
                    total_eligible=sum(
                        1
                        for r in evaluation_results
                        if r.overall_outcome == EvaluationOutcome.ELIGIBLE
                    ),
                    evaluation_duration_ms=elapsed_ms,
                )
                self.session.add(user_eval)

                for r in evaluation_results:
                    # Map domain EvaluationOutcome to database EvaluationStatus enum
                    if r.overall_outcome == EvaluationOutcome.ELIGIBLE:
                        if r.window_status == "CLOSED" or r.portal_status == "CLOSED":
                            db_status = EvaluationStatus.ELIGIBLE_OFF_CYCLE
                        else:
                            db_status = EvaluationStatus.ELIGIBLE_NOW
                    elif r.overall_outcome == EvaluationOutcome.NOT_ELIGIBLE:
                        db_status = EvaluationStatus.INELIGIBLE
                    else:
                        db_status = EvaluationStatus.CONDITIONALLY_ELIGIBLE

                    rule_res = EvaluationRuleResult(
                        result_id=uuid.uuid4(),
                        evaluation_id=user_eval.evaluation_id,
                        scheme_id=r.scheme_id,
                        version_id=r.version_id,
                        evaluation_status=db_status,
                        passed_income_check=r.passed_income_check,
                        passed_category_check=r.passed_category_check,
                        passed_domicile_check=r.passed_domicile_check,
                        passed_marks_check=r.passed_marks_check,
                        passed_course_check=r.passed_course_check,
                        missing_criteria_fields=r.missing_fields,
                        ineligibility_reasons=r.ineligibility_reasons,
                    )
                    self.session.add(rule_res)

                await self.session.commit()
            except Exception as audit_err:
                await self.session.rollback()
                logger.warning("Audit log persistence skipped or failed: %s", audit_err)

        # 4. Construct response
        response_schemes = [
            SchemeEvaluationResponse(
                scheme_id=r.scheme_id,
                scheme_title=r.scheme_title,
                overall_outcome=r.overall_outcome,
                diagnostics=[
                    RuleDiagnosticResponse(
                        clause_name=d.clause_name,
                        outcome=d.outcome,
                        explanation_en=d.explanation_en,
                        missing_fields=d.missing_fields,
                    )
                    for d in r.diagnostics
                ],
                missing_fields=r.missing_fields,
                ineligibility_reasons=r.ineligibility_reasons,
                official_source_url=r.official_source_url,
                portal_type=r.portal_type,
                portal_status=r.portal_status,
                window_status=r.window_status,
                status_label=r.status_label,
                academic_year=r.academic_year,
                window_close_date=r.window_close_date,
            )
            for r in evaluation_results
        ]

        return BatchEvaluationResponse(
            total_schemes_checked=len(evaluation_results),
            total_eligible=sum(
                1 for r in evaluation_results if r.overall_outcome == EvaluationOutcome.ELIGIBLE
            ),
            total_not_eligible=sum(
                1 for r in evaluation_results if r.overall_outcome == EvaluationOutcome.NOT_ELIGIBLE
            ),
            total_unknown=sum(
                1 for r in evaluation_results if r.overall_outcome == EvaluationOutcome.UNKNOWN
            ),
            execution_duration_ms=elapsed_ms,
            schemes=response_schemes,
        )
