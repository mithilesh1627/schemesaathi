"""Unit Tests for SHA-256 Calculation and Deduplication Logic."""

import hashlib

from src.modules.catalog.application.ingestion_service import compute_sha256


def test_compute_sha256_known_vector() -> None:
    """Verify compute_sha256 matches hashlib standard digest."""
    test_data = b"Government of Manipur Post-Matric Scholarship 2024-2025"
    expected = hashlib.sha256(test_data).hexdigest()
    actual = compute_sha256(test_data)
    assert actual == expected
    assert len(actual) == 64


def test_compute_sha256_deterministic() -> None:
    """Verify hashing the identical bytes yields exact identical hash."""
    data = b"Test Content for Deduplication Verification"
    hash1 = compute_sha256(data)
    hash2 = compute_sha256(data)
    assert hash1 == hash2


def test_compute_sha256_different_content() -> None:
    """Verify different content produces strictly different hashes."""
    data1 = b"Scholarship Document v1"
    data2 = b"Scholarship Document v2"
    assert compute_sha256(data1) != compute_sha256(data2)
