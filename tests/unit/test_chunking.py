"""Unit tests for Hierarchical Table-Preserving Chunker and PII Redaction."""

import uuid

from src.modules.retrieval.domain.chunker import (
    HierarchicalChunker,
    redact_pii_text,
)


def test_pii_unconditional_12_digit_redaction() -> None:
    """Verify any 12-digit sequence is redacted to [REDACTED_AADHAAR]."""
    text_with_aadhaar = "The student Aadhaar number is 987654321012 and mobile is 9876543210."
    redacted = redact_pii_text(text_with_aadhaar)
    assert "987654321012" not in redacted
    assert "[REDACTED_AADHAAR]" in redacted
    # 10-digit mobile number must not be corrupted
    assert "9876543210" in redacted


def test_zero_table_fracturing() -> None:
    """Verify allowance slab table is kept as an atomic non-splittable chunk."""
    chunker = HierarchicalChunker(max_tokens=512, overlap_tokens=64)
    table_md = (
        "| Group | Classification | Hosteller | Day Scholar |\n"
        "| --- | --- | --- | --- |\n"
        "| Group 1 | Degree Professional | ₹13,500 | ₹7,000 |\n"
        "| Group 2 | Diplomas | ₹9,500 | ₹6,500 |\n"
        "| Group 3 | General UG/PG | ₹7,000 | ₹4,000 |\n"
        "| Group 4 | Class 11-12 | ₹4,000 | ₹2,500 |"
    )
    sections = [
        {
            "section_title": "Maintenance Allowance Slabs",
            "is_table": True,
            "table_markdown": table_md,
            "content": "Allowance table content",
        }
    ]

    chunks = chunker.chunk_document_sections(
        scheme_id="SCH-MN-005",
        version_id=uuid.uuid4(),
        scheme_title="Post-Matric Scholarship for ST Students - Manipur",
        academic_year="2024-2025",
        sections=sections,
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.is_table is True
    assert "Group 1" in chunk.chunk_content
    assert "Group 4" in chunk.chunk_content
    # Lineage prefix must be prepended
    assert (
        "[Scheme: Post-Matric Scholarship for ST Students - Manipur | Section: Maintenance Allowance Slabs | Academic Year: 2024-2025]"
        in chunk.chunk_content
    )


def test_hierarchical_lineage_prefixing() -> None:
    """Verify every chunk carries its lineage prefix."""
    chunker = HierarchicalChunker(max_tokens=512, overlap_tokens=64)
    sections = [
        {
            "section_title": "Income Ceiling",
            "content": "Annual family income of the candidate must not exceed ₹2,50,000 per annum from all sources.",
        }
    ]

    chunks = chunker.chunk_document_sections(
        scheme_id="SCH-MN-005",
        version_id=uuid.uuid4(),
        scheme_title="Post-Matric ST Manipur",
        academic_year="2024-2025",
        sections=sections,
    )

    assert len(chunks) == 1
    prefix = "[Scheme: Post-Matric ST Manipur | Section: Income Ceiling | Academic Year: 2024-2025]"
    assert chunks[0].lineage_prefix == prefix
    assert chunks[0].chunk_content.startswith(prefix)


def test_chunk_token_limit_and_sliding_window_overlap() -> None:
    """Verify prose larger than 512 tokens splits at sentence boundaries with overlap."""
    chunker = HierarchicalChunker(max_tokens=50, overlap_tokens=15)
    sentences = [
        f"Statutory provision sentence number {i} with specific legal conditions."
        for i in range(15)
    ]
    full_text = " ".join(sentences)

    sections = [
        {
            "section_title": "Detailed Provisions",
            "content": full_text,
        }
    ]

    chunks = chunker.chunk_document_sections(
        scheme_id="SCH-MN-001",
        version_id=uuid.uuid4(),
        scheme_title="State Merit Manipur",
        academic_year="2024-2025",
        sections=sections,
    )

    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count > 0
        assert c.lineage_prefix in c.chunk_content
