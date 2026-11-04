"""Unit Tests for Aadhaar / PII In-Flight Scrubber."""

from src.core.security import redact_aadhaar_pii, validate_verhoeff


def test_verhoeff_validation() -> None:
    """Test Verhoeff algorithm on valid and invalid checksums."""
    # 999988887779 is a mathematically valid Verhoeff 12-digit sequence
    assert validate_verhoeff("999988887779") is True
    assert validate_verhoeff("9999 8888 7779") is True
    assert validate_verhoeff("9999-8888-7779") is True

    # Invalid checksums and non-12-digit lengths
    assert validate_verhoeff("999988887770") is False  # wrong check digit
    assert validate_verhoeff("234567890120") is False  # invalid checksum
    assert validate_verhoeff("12345") is False  # too short
    assert validate_verhoeff("12345678901234") is False  # too long


def test_redact_valid_aadhaar_numbers() -> None:
    """Ensure 12-digit valid Aadhaar numbers in various formats are redacted."""
    # Spaced format
    text1 = "Student Aadhaar: 9999 8888 7779 in scholarship form"
    assert redact_aadhaar_pii(text1) == "Student Aadhaar: [REDACTED_AADHAAR] in scholarship form"

    # Hyphenated format
    text2 = "Aadhaar number 9999-8888-7779 verified"
    assert redact_aadhaar_pii(text2) == "Aadhaar number [REDACTED_AADHAAR] verified"

    # Continuous 12 digits
    text3 = "UID: 999988887779"
    assert redact_aadhaar_pii(text3) == "UID: [REDACTED_AADHAAR]"


def test_redact_aadhaar_preserves_regular_numbers() -> None:
    """Ensure 10-digit phone numbers, 6-digit PIN codes, and invalid 12-digit numbers are untouched."""
    text = "Student phone: 9876543210, PIN code: 795001, Year: 2024, Invalid UID: 9999 8888 7770"
    scrubbed = redact_aadhaar_pii(text)
    assert scrubbed == text
    assert "9876543210" in scrubbed
    assert "795001" in scrubbed
    assert "9999 8888 7770" in scrubbed


def test_redact_aadhaar_empty_string() -> None:
    """Ensure empty or None string handles cleanly."""
    assert redact_aadhaar_pii("") == ""
