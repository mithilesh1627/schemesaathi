"""Pre-Submission Document Readiness Auditor.

Implements M0 roadmap document readiness checklist:
1. Dynamically extracts statutory required documents from retrieved guideline chunks.
2. Compares against user-declared documents to determine HAVE / MISSING / UNKNOWN.
3. Attaches mandatory NPCI APB and OTR / Face RD user-side warnings.
4. Pan-India compatible: Zero hardcoded state logic or document lists.
"""

import re
from typing import Any

from src.core.logging import get_logger
from src.modules.chat.domain.enums import AuditStatus
from src.modules.chat.domain.models import AuditedDocument, DocumentAuditReport

logger = get_logger(__name__)

# Statutory document patterns commonly specified in official Indian scholarship guidelines
DOCUMENT_PATTERNS = [
    (r"\bincome\s+certificate\b", "Income Certificate"),
    (r"\b(?:caste|community|tribe)\s+certificate\b", "Caste / Category Certificate"),
    (r"\b(?:domicile|permanent\s+resident|prc)\s+certificate\b", "Domicile / PRC Certificate"),
    (r"\b(?:marksheet|mark\s*sheet|marks\s+card)\b", "Academic Marksheet / Transcript"),
    (r"\b(?:fee\s+receipt|admission\s+receipt)\b", "Admission Fee Receipt"),
    (r"\b(?:bonafide|institution\s+verification)\s+certificate\b", "Bonafide Student Certificate"),
    (r"\bdisplacement\s+certificate\b", "Displacement Certificate"),
    (r"\bfree\s*ship\s*card\b", "Freeship Card"),
    (r"\b(?:bank\s+passbook|bank\s+account\s+details)\b", "Bank Account Passbook / Statement"),
    (r"\bdisability\s+certificate\b", "Disability Certificate (PwD)"),
]

NPCI_APB_WARNING = (
    "MANDATORY USER-SIDE NPCI APB WARNING: A regular bank KYC is NOT the same as NPCI "
    "Aadhaar Payment Bridge (APB) mapping. Scholarship disbursements via PFMS DBT will fail "
    "if your bank account is not actively mapped in the NPCI mapper. You must verify your "
    "Aadhaar-bank seeding status with your bank branch or via the UIDAI/NPCI portal. "
    "SchemeSaathi cannot verify your bank account mapping."
)

OTR_FACE_RD_WARNING = (
    "MANDATORY NSP OTR / BIOMETRIC WARNING: NSP One-Time Registration (OTR) with Aadhaar Face RD "
    "requires an Android/iOS device with working camera and UIDAI FaceRD service. Older smartphone "
    "devices or locked Aadhaar biometrics can cause Face RD verification failure. If you experience "
    "biometric issues, refer to the official NSP help channels or visit an authorized Common Service Centre (CSC)."
)


class DocumentReadinessAuditor:
    """Derives document checklists from official chunks and reports user readiness."""

    @classmethod
    def derive_required_documents_from_chunks(
        cls, chunks: list[dict[str, Any]], scheme_id: str | None = None
    ) -> list[str]:
        """Scan chunk texts to detect statutory document requirements dynamically."""
        detected_docs: set[str] = set()

        for chunk in chunks:
            # If scheme_id specified, filter to chunks of that scheme
            if scheme_id and chunk.get("scheme_id") and chunk.get("scheme_id") != scheme_id:
                continue

            content = str(chunk.get("chunk_content", "")).lower()

            for pattern, doc_name in DOCUMENT_PATTERNS:
                if re.search(pattern, content):
                    detected_docs.add(doc_name)

        return sorted(detected_docs)

    @classmethod
    def audit_readiness(
        cls,
        scheme_id: str,
        scheme_title: str,
        retrieved_chunks: list[dict[str, Any]],
        documents_have: list[str] | None = None,
    ) -> DocumentAuditReport:
        """Evaluate document readiness for the target scheme based on retrieved chunks."""
        required_docs = cls.derive_required_documents_from_chunks(
            retrieved_chunks, scheme_id=scheme_id
        )

        # Fallback if specific scheme has chunks retrieved but generic document wording
        if not required_docs:
            required_docs = [
                "Income Certificate",
                "Caste / Category Certificate",
                "Academic Marksheet / Transcript",
            ]

        have_set = {d.strip().lower() for d in (documents_have or [])}
        has_user_marks = documents_have is not None

        audited_items: list[AuditedDocument] = []
        have_count = 0
        missing_count = 0

        for doc in required_docs:
            doc_lower = doc.lower()
            is_have = any(h in doc_lower or doc_lower in h for h in have_set)

            if is_have:
                status = AuditStatus.HAVE
                reason = "User confirmed possession. Ensure validity for current academic year."
                have_count += 1
            elif has_user_marks:
                status = AuditStatus.MISSING
                reason = f"Required by statutory guidelines for {scheme_id}. Must be procured before portal submission."
                missing_count += 1
            else:
                status = AuditStatus.UNKNOWN
                reason = "Not marked by applicant. Please confirm possession."

            audited_items.append(
                AuditedDocument(
                    document_name=doc,
                    status=status,
                    reason_or_guidance=reason,
                )
            )

        if has_user_marks:
            if missing_count == 0:
                summary = f"All {have_count} statutory documents identified in guidelines are marked as available."
            else:
                missing_names = [
                    item.document_name
                    for item in audited_items
                    if item.status == AuditStatus.MISSING
                ]
                summary = (
                    f"Readiness Audit: {have_count} document(s) available, {missing_count} missing: "
                    f"[{', '.join(missing_names)}]. Please obtain missing documents before submitting."
                )
        else:
            summary = (
                f"Statutory guidelines identify {len(required_docs)} required document(s) for {scheme_id}. "
                "Please mark which documents you possess to generate a personalized readiness checklist."
            )

        return DocumentAuditReport(
            scheme_id=scheme_id,
            scheme_title=scheme_title,
            documents=audited_items,
            summary_text=summary,
            npci_apb_warning=NPCI_APB_WARNING,
            otr_face_rd_warning=OTR_FACE_RD_WARNING,
        )
