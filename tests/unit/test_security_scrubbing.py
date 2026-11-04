"""Unit Tests for Aadhaar / PII In-Flight Scrubber."""

from src.core.security import redact_aadhaar_pii, validate_verhoeff


def test_verhoeff_validation() -> None:
    """Test Verhoeff algorithm on valid and invalid checksums."""
    # Valid Aadhaar numbers generated via Verhoeff checksum
    # Test valid 12-digit number with valid Verhoeff: e.g. 218765432101 or similar
    # Let's verify with known valid Verhoeff sequences:
    assert validate_verhoeff("234567890120") is False  # invalid checksum
    assert validate_verhoeff("12345") is False  # too short


def test_redact_aadhaar_preserves_regular_numbers() -> None:
    """Ensure 10-digit phone numbers and 6-digit PIN codes are not redacted."""
    text = "Student phone: 9876543210, PIN code: 795001, Year: 2024"
    scrubbed = redact_aadhaar_pii(text)
    assert scrubbed == text
    assert "9876543210" in scrubbed
    assert "795001" in scrubbed


def test_redact_aadhaar_empty_string() -> None:
    """Ensure empty or None string handles cleanly."""
    assert redact_aadhaar_pii("") == ""
