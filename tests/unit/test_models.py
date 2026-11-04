"""Unit Tests for SQLAlchemy Domain Models."""

from src.modules.catalog.domain.enums import SchemeLevel, VerificationStatus
from src.modules.catalog.domain.models import Scheme, SchemeVersion


def test_scheme_model_instantiation() -> None:
    """Verify Scheme domain model attributes."""
    scheme = Scheme(
        scheme_id="sch-mn-005",
        official_code="MANIPUR_ST_POST_MATRIC",
        title_en="Post-Matric Scholarship for ST Students - Manipur",
        title_mni_beng="ꯃꯅꯤꯄꯨꯔꯒꯤ ST ꯃꯆꯥꯁꯤꯡꯒꯤ ꯄꯣꯁ꯭ꯠ-ꯃꯦꯠꯔꯤꯛ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ",
        issuing_level=SchemeLevel.CENTRALLY_SPONSORED,
        ministry_or_department="Department of Tribal Affairs & Hills, Manipur",
        implementing_agency="Government of Manipur",
        canonical_source_url="https://tahmanipur.gov.in",
        guidelines_document_url="https://scholarships.gov.in",
        is_active=True,
    )

    assert scheme.scheme_id == "sch-mn-005"
    assert scheme.issuing_level == SchemeLevel.CENTRALLY_SPONSORED
    assert scheme.is_active is True


def test_scheme_version_model_instantiation() -> None:
    """Verify SchemeVersion domain model attributes and defaults."""
    version = SchemeVersion(
        scheme_id="sch-mn-005",
        version_number=1,
        academic_year="2024-2025",
        content_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        verification_status=VerificationStatus.OFFICIAL_PROVISIONAL,
    )

    assert version.scheme_id == "sch-mn-005"
    assert version.version_number == 1
    assert version.academic_year == "2024-2025"
    assert version.verification_status == VerificationStatus.OFFICIAL_PROVISIONAL
