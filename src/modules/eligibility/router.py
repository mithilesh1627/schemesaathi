"""FastAPI Router for Deterministic Scheme Eligibility Evaluation."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.eligibility.application.evaluator_service import EligibilityEvaluatorService
from src.modules.eligibility.application.schemas import (
    BatchEvaluationResponse,
    StudentProfileRequest,
)

router = APIRouter(prefix="/eligibility", tags=["Eligibility Evaluation Engine"])


@router.post(
    "/evaluate",
    response_model=BatchEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Student Profile Against Statutory Scheme Rules",
    description=(
        "Pure deterministic statutory evaluation of citizen/student criteria against active "
        "government schemes. Zero LLM, zero Aadhaar storage. Evaluates against latest verified "
        "rules and returns per-rule explanations with official government portal references."
    ),
)
async def evaluate_eligibility(
    profile_request: StudentProfileRequest,
    db: AsyncSession = Depends(get_db_session),
) -> BatchEvaluationResponse:
    """Evaluate student profile against all active schemes deterministically."""
    service = EligibilityEvaluatorService(db)
    return await service.evaluate_student_profile(profile_request, persist_audit=True)
