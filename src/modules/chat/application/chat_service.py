"""Application Orchestrator for Grounded Chat, State Synchronization, and Citations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.security import redact_pii_text
from src.modules.chat.application.auditor import DocumentReadinessAuditor
from src.modules.chat.application.citation_checker import (
    STANDARD_REFUSAL_MESSAGE,
    CitationEngine,
)
from src.modules.chat.application.prompt_builder import ChatPromptBuilder
from src.modules.chat.application.schemas import (
    AuditedDocumentItem,
    ChatMessageRequest,
    ChatMessageResponse,
    CitationResponse,
    DocumentAuditResult,
    EligibilityItemResult,
)
from src.modules.chat.application.synchronizer import DeterministicStateSynchronizer
from src.modules.chat.domain.enums import LanguageScript
from src.modules.chat.domain.models import ChatSession
from src.modules.chat.infrastructure.llm_provider import BaseLlmProvider, get_llm_provider
from src.modules.chat.infrastructure.session_repository import (
    ChatSessionRepository,
    get_session_repository,
)
from src.modules.eligibility.application.evaluator_service import EligibilityEvaluatorService
from src.modules.eligibility.application.schemas import StudentProfileRequest
from src.modules.retrieval.application.retrieval_service import RetrievalService
from src.modules.retrieval.domain.models import QueryScript
from src.modules.retrieval.domain.script_router import ScriptRouter

logger = get_logger(__name__)


class ChatService:
    """Orchestrates grounded conversational turns with deterministic state synchronization."""

    def __init__(
        self,
        db_session: AsyncSession,
        session_repo: ChatSessionRepository | None = None,
        llm_provider: BaseLlmProvider | None = None,
    ) -> None:
        self.db_session = db_session
        self.session_repo = session_repo or get_session_repository()
        self.llm_provider = llm_provider or get_llm_provider()
        self.retrieval_service = RetrievalService(db_session)
        self.script_router = ScriptRouter()
        self.evaluator_service = EligibilityEvaluatorService(db_session)

    async def get_or_create_session(self, session_id: str) -> ChatSession:
        """Fetch existing active session or initialize new one."""
        session = await self.session_repo.get(session_id)
        if session is None:
            session = ChatSession(session_id=session_id)
            await self.session_repo.save(session)
        return session

    def detect_script_and_language(self, text: str) -> tuple[LanguageScript, bool]:
        """Detect language and script using existing Sprint 3 script router."""
        routing = self.script_router.route_query(text)
        script_enum = routing.detected_script

        if script_enum == QueryScript.MEETEI_MAYEK:
            return LanguageScript.MNI_MTEI, False
        elif script_enum == QueryScript.BENGALI:
            return LanguageScript.MNI_BENG, False
        elif script_enum == QueryScript.LATIN:
            if routing.is_transliterated or routing.mapped_terms:
                return LanguageScript.MNI_LATN, False
            return LanguageScript.ENGLISH, False

        # Fallback to English if unclassifiable
        return LanguageScript.ENGLISH, True

    async def process_turn(self, request: ChatMessageRequest) -> ChatMessageResponse:
        """Execute full 5-stage conversational pipeline."""
        # Step 0: Unconditional 12-digit Aadhaar redaction
        clean_message = redact_pii_text(request.message)

        # Retrieve or initialize session
        session = await self.get_or_create_session(request.session_id)

        # Step 1: Detect script/language with Sprint 3 script router
        detected_lang, fallback_en = self.detect_script_and_language(clean_message)

        # Step 2: Deterministic State Synchronization (Apply updates)
        profile_changes = DeterministicStateSynchronizer.apply_updates(
            session=session,
            updates=request.profile_updates,
            message_text=clean_message,
        )

        # Step 3: Run Deterministic Eligibility Engine if asked or profile updated
        is_eligibility_query = any(
            word in clean_message.lower()
            for word in [
                "eligible",
                "eligibility",
                "qualify",
                "can i apply",
                "am i",
                "scheme for me",
            ]
        ) or bool(profile_changes)

        eligibility_eval = None
        structured_eligibility_items: list[EligibilityItemResult] | None = None

        if is_eligibility_query:
            facts = session.profile_facts
            # Only evaluate if minimum facts (e.g. social category or income or domicile) exist
            if (
                facts.domicile_state
                or facts.social_category
                or facts.annual_family_income_inr is not None
            ):
                profile_req = StudentProfileRequest(
                    domicile_state=facts.domicile_state or "MANIPUR",
                    social_category=facts.social_category or "GENERAL",
                    annual_family_income_inr=facts.annual_family_income_inr
                    if facts.annual_family_income_inr is not None
                    else 0.0,
                    course_level=facts.course_level or "UNDERGRADUATE",
                    marks_percent=facts.marks_percent,
                    gender=facts.gender or "ANY",
                    is_displaced=facts.is_displaced if facts.is_displaced is not None else False,
                    session_id=session.session_id,
                )
                try:
                    batch_resp = await self.evaluator_service.evaluate_student_profile(
                        profile_req, persist_audit=False
                    )
                    eligibility_eval = batch_resp
                    structured_eligibility_items = [
                        EligibilityItemResult(
                            scheme_id=r.scheme_id,
                            scheme_title=r.scheme_title,
                            status=r.overall_outcome.value,
                            reason="; ".join(r.ineligibility_reasons)
                            if r.ineligibility_reasons
                            else "Criteria satisfied.",
                            rule_description="; ".join(d.explanation_en for d in r.diagnostics),
                        )
                        for r in batch_resp.schemes
                    ]
                except Exception as exc:
                    logger.warning("Deterministic eligibility evaluation failed in chat: %s", exc)

        # Step 4: Hybrid Retrieval using existing Sprint 3 service
        search_res = await self.retrieval_service.search(
            query=clean_message,
            top_k=5,
            state_filter=session.profile_facts.domicile_state,
        )

        raw_candidates = search_res.get("results", [])
        retrieved_chunks: list[dict[str, Any]] = []
        for c in raw_candidates:
            if hasattr(c, "chunk_id"):
                retrieved_chunks.append(
                    {
                        "chunk_id": str(c.chunk_id),
                        "scheme_id": c.scheme_id,
                        "version_id": str(c.version_id),
                        "section_title": c.section_title,
                        "chunk_content": c.chunk_content,
                        "token_count": c.token_count,
                        "page_number": c.page_number,
                        "source_url": c.source_url,
                        "content_sha256": c.document_sha256,
                        "academic_year": c.academic_year,
                        "window_close_date": str(c.window_close_date)
                        if c.window_close_date
                        else None,
                        "portal_status": c.portal_status,
                    }
                )
            elif isinstance(c, dict):
                retrieved_chunks.append(c)

        routed_query = search_res.get("expanded_query", clean_message)
        invented_chunk_count = search_res.get("invented_chunk_count", 0)

        # Step 5: Document Readiness Auditor (if requested or relevant)
        audit_res: DocumentAuditResult | None = None
        is_doc_turn = request.documents_have is not None or any(
            w in clean_message.lower()
            for w in ["document", "docs", "certificate", "checklist", "ready", "audit"]
        )

        if is_doc_turn and retrieved_chunks:
            target_scheme = request.scheme_context or retrieved_chunks[0].get(
                "scheme_id", "SCH-MN-005"
            )
            target_title = retrieved_chunks[0].get("scheme_id", "Statutory Scheme")
            audit_report = DocumentReadinessAuditor.audit_readiness(
                scheme_id=target_scheme,
                scheme_title=target_title,
                retrieved_chunks=retrieved_chunks,
                documents_have=request.documents_have,
            )
            audit_res = DocumentAuditResult(
                scheme_id=audit_report.scheme_id,
                scheme_title=audit_report.scheme_title,
                documents=[
                    AuditedDocumentItem(
                        document_name=d.document_name,
                        status=d.status.value,
                        reason_or_guidance=d.reason_or_guidance,
                    )
                    for d in audit_report.documents
                ],
                summary_text=audit_report.summary_text,
                npci_apb_warning=audit_report.npci_apb_warning,
                otr_face_rd_warning=audit_report.otr_face_rd_warning,
            )

        # Step 6: Compose Synchronizer State String
        synchronizer_str = DeterministicStateSynchronizer.serialize_synchronizer_state(
            facts=session.profile_facts,
            eligibility_eval=eligibility_eval,
        )

        # Step 7: Build Grounded Prompt
        prompt = ChatPromptBuilder.build_prompt(
            user_message=clean_message,
            retrieved_chunks=retrieved_chunks,
            synchronizer_state_str=synchronizer_str,
            conversation_history=session.history,
            detected_script=detected_lang,
        )

        # Step 8: LLM Generation
        raw_answer = self.llm_provider.generate(
            prompt=prompt,
            retrieved_chunks=retrieved_chunks,
            synchronizer_state_str=synchronizer_str,
            user_message=clean_message,
            detected_script=detected_lang,
        )

        # Step 9: Citation Verification and Grounding Check
        is_valid, final_answer, resolved_citations = CitationEngine.validate_and_resolve_citations(
            answer_text=raw_answer,
            retrieved_chunks=retrieved_chunks,
            is_eligibility_only_turn=is_eligibility_query and not retrieved_chunks,
        )

        # Step 10: Update Bounded Session History
        session.add_user_message(clean_message)
        session.add_assistant_message(final_answer, resolved_citations)
        session.last_retrieved_chunks = retrieved_chunks
        await self.session_repo.save(session)

        is_refusal = final_answer == STANDARD_REFUSAL_MESSAGE

        return ChatMessageResponse(
            session_id=session.session_id,
            answer=final_answer,
            citations=[
                CitationResponse(
                    citation_number=c.citation_number,
                    chunk_id=c.chunk_id,
                    scheme_id=c.scheme_id,
                    section=c.section,
                    source_url=c.source_url,
                    content_sha256=c.content_sha256,
                    academic_year=c.academic_year,
                    window_close_date=c.window_close_date,
                    portal_status=c.portal_status,
                )
                for c in resolved_citations
            ],
            routed_query=routed_query,
            detected_language=detected_lang.value,
            fallback_to_english=fallback_en,
            chunks_retrieved_count=len(retrieved_chunks),
            invented_chunk_count=invented_chunk_count,
            eligibility_results=structured_eligibility_items,
            document_audit=audit_res,
            is_refusal=is_refusal,
        )
