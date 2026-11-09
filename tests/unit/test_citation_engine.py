"""Unit tests for CitationEngine and Grounding Checks."""

from src.modules.chat.application.citation_checker import (
    STANDARD_REFUSAL_MESSAGE,
    CitationEngine,
)


def test_valid_citations_resolve_to_retrieved_chunks() -> None:
    """Verify citations correctly map to authentic retrieved chunks with verified numeric grounding."""
    retrieved_chunks = [
        {
            "chunk_id": "chunk-111",
            "scheme_id": "SCH-MN-005",
            "section_title": "Maintenance Allowance",
            "chunk_content": "Maintenance allowance is 550 per month for day scholars and 1200 per month for hostellers.",
            "source_url": "https://scholarships.gov.in/st.pdf",
            "content_sha256": "eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe",
            "academic_year": "2024-2025",
            "window_close_date": "2024-11-30",
            "portal_status": "OPEN",
        },
        {
            "chunk_id": "chunk-222",
            "scheme_id": "SCH-MN-001",
            "section_title": "Merit Stipend",
            "chunk_content": "Up to ₹7,500 per annum merit stipend disbursed via PFMS.",
            "source_url": "https://scholarships.gov.in/merit.pdf",
            "content_sha256": "9596807e57debb7b141d18815054363e130a4e7cd454f5bea58598a6ce7ae22c",
            "academic_year": "2024-2025",
            "window_close_date": "2024-11-30",
            "portal_status": "OPEN",
        },
    ]

    answer = "The maintenance allowance is ₹550 per month [^1] and merit stipend is ₹7,500 per annum [^2]."
    is_valid, final_ans, citations = CitationEngine.validate_and_resolve_citations(
        answer_text=answer,
        retrieved_chunks=retrieved_chunks,
    )

    assert is_valid is True
    assert final_ans == answer
    assert len(citations) == 2
    assert citations[0].citation_number == 1
    assert citations[0].chunk_id == "chunk-111"
    assert citations[0].scheme_id == "SCH-MN-005"
    assert citations[1].citation_number == 2
    assert citations[1].chunk_id == "chunk-222"
    assert citations[1].scheme_id == "SCH-MN-001"


def test_numeric_claim_verification_rejects_hallucinated_number() -> None:
    """Verify numeric grounding fails closed to standard refusal when number is missing from chunk."""
    retrieved_chunks = [
        {
            "chunk_id": "chunk-111",
            "scheme_id": "SCH-MN-005",
            "section_title": "Maintenance Allowance",
            "chunk_content": "Maintenance allowance is 550 per month for day scholars and 1200 per month for hostellers.",
            "source_url": "https://scholarships.gov.in/st.pdf",
        }
    ]

    # Cites 13,500 which does not appear in the ST guideline chunk
    hallucinated_answer = (
        "Under the official guidelines [^1], the maintenance allowance is ₹13,500 per month [^1]."
    )
    is_valid, final_ans, citations = CitationEngine.validate_and_resolve_citations(
        answer_text=hallucinated_answer,
        retrieved_chunks=retrieved_chunks,
    )

    assert is_valid is False
    assert final_ans == STANDARD_REFUSAL_MESSAGE
    assert len(citations) == 0


def test_numeric_claim_verification_rejects_wrong_unit() -> None:
    """Verify numeric grounding fails closed when periodic unit (per annum vs per month) is wrong."""
    retrieved_chunks = [
        {
            "chunk_id": "chunk-111",
            "scheme_id": "SCH-MN-005",
            "section_title": "Maintenance Allowance",
            "chunk_content": "Maintenance allowance is 550 per month for day scholars and 1200 per month for hostellers.",
            "source_url": "https://scholarships.gov.in/st.pdf",
        }
    ]

    # Claims per annum when the chunk specifies per month
    wrong_unit_answer = (
        "Under the official guidelines [^1], the maintenance allowance is ₹550 per annum [^1]."
    )
    is_valid, final_ans, citations = CitationEngine.validate_and_resolve_citations(
        answer_text=wrong_unit_answer,
        retrieved_chunks=retrieved_chunks,
    )

    assert is_valid is False
    assert final_ans == STANDARD_REFUSAL_MESSAGE
    assert len(citations) == 0


def test_out_of_range_citation_fails_and_returns_refusal() -> None:
    """Verify citation referencing nonexistent chunk index triggers standard refusal."""
    retrieved_chunks = [
        {
            "chunk_id": "chunk-111",
            "scheme_id": "SCH-MN-005",
            "source_url": "https://scholarships.gov.in/st.pdf",
        }
    ]

    # Cites [^5] when only 1 chunk was retrieved
    answer = "The allowance is ₹10,000 [^5]."
    is_valid, final_ans, citations = CitationEngine.validate_and_resolve_citations(
        answer_text=answer,
        retrieved_chunks=retrieved_chunks,
    )

    assert is_valid is False
    assert final_ans == STANDARD_REFUSAL_MESSAGE
    assert len(citations) == 0


def test_uncited_factual_claim_fails_grounding_and_refuses() -> None:
    """Verify answer without any citations returns standard refusal."""
    retrieved_chunks = [
        {
            "chunk_id": "chunk-111",
            "scheme_id": "SCH-MN-005",
            "source_url": "https://scholarships.gov.in/st.pdf",
        }
    ]

    # No citations anywhere in answer
    answer = "The maintenance allowance is ₹7,000 for day scholars."
    is_valid, final_ans, citations = CitationEngine.validate_and_resolve_citations(
        answer_text=answer,
        retrieved_chunks=retrieved_chunks,
    )

    assert is_valid is False
    assert final_ans == STANDARD_REFUSAL_MESSAGE
    assert len(citations) == 0


def test_refusal_form_passes_citation_check_cleanly() -> None:
    """Verify that an explicit standard refusal message passes verification with 0 citations."""
    is_valid, final_ans, citations = CitationEngine.validate_and_resolve_citations(
        answer_text=STANDARD_REFUSAL_MESSAGE,
        retrieved_chunks=[],
    )

    assert is_valid is True
    assert final_ans == STANDARD_REFUSAL_MESSAGE
    assert len(citations) == 0


def test_strengthened_grounding_check_rejects_numeric_claim_whose_sentence_carries_no_citation_marker() -> (
    None
):
    """Verify strengthened numeric grounding check rejects a numeric claim whose sentence carries no citation marker."""
    retrieved_chunks = [
        {
            "chunk_id": "chunk-111",
            "scheme_id": "SCH-MN-005",
            "section_title": "Maintenance Allowance",
            "chunk_content": "Group-I: Hostellers 1200, Day Scholars 550 per month. Group-II: Hostellers 820, Day Scholars 530.",
            "source_url": "https://scholarships.gov.in/st.pdf",
            "academic_year": "2024-2025",
        }
    ]

    # Case A: Answer has no citation markers anywhere, sentence claims ₹7,000
    answer_no_cits = "The maintenance allowance is ₹7,000 per month."
    is_valid_a, reason_a = CitationEngine.verify_numeric_grounding(answer_no_cits, retrieved_chunks)
    assert is_valid_a is False
    assert "carries no citation marker" in str(reason_a)

    # Case B: Answer has a citation on line 1, but sentence on line 2 claims ungrounded ₹7,000 without citation marker
    answer_multi_line = (
        "[^1] Guidelines for Post-Matric ST.\nThe maintenance allowance is ₹7,000 per month."
    )
    is_valid_b, reason_b = CitationEngine.verify_numeric_grounding(
        answer_multi_line, retrieved_chunks
    )
    assert is_valid_b is False
    assert "7,000" in str(reason_b)


def test_strengthened_grounding_check_rejects_unqualified_rate_for_multigroup_scheme() -> None:
    """Verify that claiming an unqualified single rate for a multi-group scheme is rejected."""
    retrieved_chunks = [
        {
            "chunk_id": "chunk-111",
            "scheme_id": "SCH-MN-005",
            "section_title": "Maintenance Allowance Slabs",
            "chunk_content": "Group-I: 1200 550. Group - II: 820 530. Group - III: 570 300. Group- IV: 380 230 per month.",
            "source_url": "https://scholarships.gov.in/st.pdf",
            "academic_year": "2024-2025",
        }
    ]

    # Answer asserts ₹300 per month as the unqualified rate without group qualification
    unqualified_ans = "[^1] According to SCH-MN-005 [^1], the maintenance allowance for Post-Matric ST day scholars is ₹300 per month [^1]."
    is_valid, reason = CitationEngine.verify_numeric_grounding(unqualified_ans, retrieved_chunks)
    assert is_valid is False
    assert "group-qualified" in str(reason).lower()
