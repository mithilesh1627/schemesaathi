"""Unit test for ScannedPdfOcrExtractor with pypdfium2 and PaddleOCR."""

import io

from reportlab.pdfgen import canvas

from src.modules.retrieval.infrastructure.extractors import ScannedPdfOcrExtractor


def create_test_scanned_pdf(text_lines: list[str]) -> bytes:
    """Generate a single-page PDF with synthetic text to simulate a scanned document."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 750
    for line in text_lines:
        c.drawString(50, y, line)
        y -= 30
    c.save()
    return buf.getvalue()


def test_ocr_extractor_text_recovery_and_pii_redaction() -> None:
    """Verify ScannedPdfOcrExtractor recovers rendered text and redacts 12-digit Aadhaar sequences."""
    test_lines = [
        "SCHEMESAATHI STATUTORY SCHEME OCR RECOVERY",
        "DIRECTORATE OF HIGHER EDUCATION MANIPUR",
        "Aadhaar Number 987654321098 is strictly confidential",
    ]
    pdf_bytes = create_test_scanned_pdf(test_lines)

    extractor = ScannedPdfOcrExtractor()
    assert extractor.is_available() is True

    result = extractor.extract(
        pdf_bytes=pdf_bytes,
        source_name="test_order.pdf",
        source_url="https://highereducationmanipur.gov.in/order.pdf",
    )

    assert result.extraction_mode == "OCR"
    assert result.page_count == 1
    assert result.character_count > 0
    assert len(result.content_sha256) == 64

    # The recovered text should contain words from the document
    normalized_text = result.raw_text.replace(" ", "").upper()
    assert "SCHEMESAATHI" in normalized_text
    assert "MANIPUR" in normalized_text

    # 12-digit Aadhaar pattern must be unconditionally redacted
    assert "987654321098" not in result.raw_text
    assert "[REDACTED_AADHAAR]" in result.raw_text
