"""Unit tests for DocumentReadinessAuditor."""

from src.modules.chat.application.auditor import (
    NPCI_APB_WARNING,
    OTR_FACE_RD_WARNING,
    DocumentReadinessAuditor,
)
from src.modules.chat.domain.enums import AuditStatus


def test_derive_required_documents_from_chunks() -> None:
    """Verify document auditor extracts statutory document requirements dynamically from chunk text."""
    chunks = [
        {
            "scheme_id": "SCH-MN-005",
            "chunk_content": (
                "Applicants must upload an Income Certificate issued by an Executive Magistrate. "
                "Caste Certificate issued by the competent district authority must also be attached. "
                "Permanent Resident Certificate (PRC) is mandatory for domicile verification."
            ),
        },
        {
            "scheme_id": "SCH-MN-005",
            "chunk_content": "A copy of the previous academic marksheet and admission fee receipt must be produced.",
        },
    ]

    docs = DocumentReadinessAuditor.derive_required_documents_from_chunks(
        chunks, scheme_id="SCH-MN-005"
    )

    assert "Income Certificate" in docs
    assert "Caste / Category Certificate" in docs
    assert "Domicile / PRC Certificate" in docs
    assert "Academic Marksheet / Transcript" in docs
    assert "Admission Fee Receipt" in docs
    assert len(docs) == 5


def test_audit_readiness_with_user_marks_and_warnings() -> None:
    """Verify auditor correctly evaluates HAVE and MISSING documents and attaches warnings."""
    chunks = [
        {
            "scheme_id": "SCH-MN-005",
            "chunk_content": "Requires Income Certificate, Caste Certificate, and Marksheet.",
        }
    ]

    # User marks only Income Certificate and Caste Certificate
    user_docs = ["Income Certificate", "Caste / Category Certificate"]

    report = DocumentReadinessAuditor.audit_readiness(
        scheme_id="SCH-MN-005",
        scheme_title="Post-Matric ST",
        retrieved_chunks=chunks,
        documents_have=user_docs,
    )

    doc_map = {d.document_name: d.status for d in report.documents}
    assert doc_map["Income Certificate"] == AuditStatus.HAVE
    assert doc_map["Caste / Category Certificate"] == AuditStatus.HAVE
    assert doc_map["Academic Marksheet / Transcript"] == AuditStatus.MISSING

    # Mandatory user-side warnings must be present
    assert NPCI_APB_WARNING in report.npci_apb_warning
    assert "A regular bank KYC is NOT the same as NPCI" in report.npci_apb_warning
    assert OTR_FACE_RD_WARNING in report.otr_face_rd_warning
    assert "NSP One-Time Registration (OTR) with Aadhaar Face RD" in report.otr_face_rd_warning


def test_audit_readiness_without_user_marks_returns_unknown() -> None:
    """Verify when user hasn't marked documents, auditor returns UNKNOWN status."""
    chunks = [
        {
            "scheme_id": "SCH-MN-003",
            "chunk_content": "Eligible students must submit Displacement Certificate and Admission Fee Receipt.",
        }
    ]

    report = DocumentReadinessAuditor.audit_readiness(
        scheme_id="SCH-MN-003",
        scheme_title="CMCSRS Displaced",
        retrieved_chunks=chunks,
        documents_have=None,  # No marks
    )

    for doc in report.documents:
        assert doc.status == AuditStatus.UNKNOWN
