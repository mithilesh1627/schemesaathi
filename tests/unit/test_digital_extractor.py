"""Unit tests for DigitalPdfExtractor and authentic table extraction."""

from pathlib import Path

from src.modules.retrieval.infrastructure.extractors import (
    DigitalPdfExtractor,
    extract_tables_from_digital_text,
)


def test_digital_pdf_extractor_tables_populated_from_real_document() -> None:
    """Verify DigitalPdfExtractor.tables is populated with authentic tables extracted from real PDFs."""
    # Test with authentic SCH-MN-005 PDF (Post-Matric ST)
    doc_path = Path(
        "data/storage/documents/eb/eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe.pdf"
    )
    assert doc_path.exists(), "Authentic guideline document must exist on disk"

    pdf_bytes = doc_path.read_bytes()
    result = DigitalPdfExtractor.extract(
        pdf_bytes=pdf_bytes,
        source_name="st_guidelines.pdf",
        source_url="https://scholarships.gov.in/public/schemeGuidelines/EDUPostMatricScholarshipPMSforSTstudents.pdf",
    )

    assert result.extraction_mode == "DIGITAL_TEXT"
    assert result.page_count == 4
    assert result.character_count > 5000
    assert (
        result.content_sha256 == "eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe"
    )

    # Verify tables property is authentically populated
    assert len(result.tables) >= 1
    st_table = result.tables[0]
    assert st_table["table_name"] == "Maintenance Allowance Slabs"
    assert "| Group |" in st_table["table_markdown"]
    assert "Group-I" in st_table["table_markdown"]
    assert "1200" in st_table["table_markdown"]
    assert "550" in st_table["table_markdown"]


def test_extract_tables_from_digital_text_pre_matric() -> None:
    """Verify table extraction for Pre-Matric ST scholarship grant rates."""
    sample_text = (
        "The rates of scholarship and other grant will be as follows:\n"
        "Scholarship for 10 months 225 2250 525 5250\n"
        "Books and ad hoc Grant    750   1000\n"
    )
    tables = extract_tables_from_digital_text(sample_text)
    assert len(tables) == 1
    assert tables[0]["table_name"] == "Pre-Matric Rates and Book Grant Table"
    assert "2250" in tables[0]["table_markdown"]
    assert "5250" in tables[0]["table_markdown"]


def test_extract_tables_from_digital_text_pm_yasasvi() -> None:
    """Verify table extraction for PM-YASASVI OBC allowance table."""
    sample_text = (
        "Category of courses Yearly (in Rs) Academic Allowance Tuition Fee Total\n"
        "Group 1: Degree and Post Graduate level professional courses 10000 10000 20000\n"
        "Group 2: Other Professional Courses leading to Degree, Diploma, Certificate 8000 5000 13000\n"
        "Group 3: Graduate and Post Graduate courses not covered under Group I & Group II 6000 2000 8000\n"
        "Group 4: All post-matriculation (Post Class X level) non-degree courses 5000 0 5000\n"
    )
    tables = extract_tables_from_digital_text(sample_text)
    assert len(tables) == 1
    assert tables[0]["table_name"] == "PM-YASASVI Group Maintenance Slabs"
    assert "20000" in tables[0]["table_markdown"]
    assert "13000" in tables[0]["table_markdown"]
