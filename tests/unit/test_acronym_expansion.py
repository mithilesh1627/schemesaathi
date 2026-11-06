"""Unit tests for domain acronym expansion engine."""

from src.modules.retrieval.domain.acronyms import OFFICIAL_ACRONYMS, expand_query_acronyms


def test_official_acronyms_presence() -> None:
    """Verify all M0 statutory acronyms are present in the dictionary."""
    expected = ["OTR", "NSP", "AISHE", "NPCI", "CMCSRS", "Face RD", "DBT", "PFMS"]
    for ac in expected:
        assert ac in OFFICIAL_ACRONYMS


def test_acronym_expansion_single() -> None:
    """Verify single acronym expansion."""
    q = "how to do OTR registration"
    expanded, found = expand_query_acronyms(q)
    assert "OTR (One Time Registration)" in found
    assert "One Time Registration" in expanded


def test_acronym_expansion_multiple() -> None:
    """Verify multiple acronyms in a single query."""
    q = "NSP portal OTR Face RD"
    expanded, found = expand_query_acronyms(q)
    assert len(found) >= 3
    assert "National Scholarship Portal" in expanded
    assert "One Time Registration" in expanded
    assert "Aadhaar Face Registered Device" in expanded


def test_no_acronym_unchanged() -> None:
    """Verify query with no acronyms is unmodified."""
    q = "state merit scholarship for college degree"
    expanded, found = expand_query_acronyms(q)
    assert len(found) == 0
    assert expanded == q
