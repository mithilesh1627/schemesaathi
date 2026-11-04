"""Verified Official Government Source Registry Service."""

from src.modules.catalog.application.schemas import (
    SourceRegistryItem,
    SourceRegistryResponse,
)

# Immutable Registry of Audited Official Sources from Milestone M0
OFFICIAL_SOURCES: list[dict[str, object]] = [
    {
        "registry_id": "SRC-CEN-01",
        "authority_name": "Ministry of Electronics & IT / NeGD - National Scholarship Portal (NSP)",
        "portal_url": "https://scholarships.gov.in",
        "domain_type": "CENTRAL_PORTAL",
        "schemes_covered": ["Centrally Sponsored Schemes", "Central Sector Schemes", "UGC/AICTE"],
        "update_cadence": "Daily during open window (July-Dec); Weekly off-cycle",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-02",
        "authority_name": "Ministry of Electronics & IT / NeGD - myScheme Portal",
        "portal_url": "https://myscheme.gov.in",
        "domain_type": "CENTRAL_AGGREGATOR",
        "schemes_covered": ["Central & State Discovery Metadata", "Scheme Eligibility Checklists"],
        "update_cadence": "Bi-weekly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-03",
        "authority_name": "National e-Governance Division (NeGD) - UMANG Platform",
        "portal_url": "https://web.umang.gov.in",
        "domain_type": "CENTRAL_MOBILE_SERVICE",
        "schemes_covered": ["NSP Services", "Eligibility Directory", "Status Tracking"],
        "update_cadence": "Monthly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-04",
        "authority_name": "Ministry of Tribal Affairs (MoTA)",
        "portal_url": "https://tribal.nic.in",
        "domain_type": "CENTRAL_MINISTRY",
        "schemes_covered": [
            "Pre-Matric ST",
            "Post-Matric ST",
            "Top Class ST",
            "National Overseas ST",
        ],
        "update_cadence": "Monthly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-05",
        "authority_name": "Ministry of Social Justice & Empowerment (MoSJE)",
        "portal_url": "https://socialjustice.gov.in",
        "domain_type": "CENTRAL_MINISTRY",
        "schemes_covered": ["PM-YASASVI", "Top Class SC", "Post-Matric SC", "National Overseas SC"],
        "update_cadence": "Monthly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-06",
        "authority_name": "Ministry of Minority Affairs (MoMA)",
        "portal_url": "https://minorityaffairs.gov.in",
        "domain_type": "CENTRAL_MINISTRY",
        "schemes_covered": [
            "Pre-Matric Minorities",
            "Post-Matric Minorities",
            "Merit-cum-Means (MCM)",
        ],
        "update_cadence": "Monthly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-07",
        "authority_name": "Ministry of Education (MoE) - Higher Education & DSEL",
        "portal_url": "https://education.gov.in",
        "domain_type": "CENTRAL_MINISTRY",
        "schemes_covered": ["PM-USP CSSS", "NMMSS"],
        "update_cadence": "Quarterly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-08",
        "authority_name": "University Grants Commission (UGC)",
        "portal_url": "https://ugc.gov.in",
        "domain_type": "STATUTORY_BODY",
        "schemes_covered": ["Ishan Uday (NER)", "PG Single Girl Child", "PG Rank Holders"],
        "update_cadence": "Bi-weekly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-09",
        "authority_name": "All India Council for Technical Education (AICTE)",
        "portal_url": "https://aicte-india.org",
        "domain_type": "STATUTORY_BODY",
        "schemes_covered": ["AICTE Pragati", "AICTE Saksham", "AICTE Swanath"],
        "update_cadence": "Monthly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-CEN-10",
        "authority_name": "North Eastern Council (NEC) / MoDoNER",
        "portal_url": "https://necouncil.gov.in",
        "domain_type": "REGIONAL_STATUTORY_COUNCIL",
        "schemes_covered": ["NEC Merit Scholarship for NER Students"],
        "update_cadence": "Monthly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-MN-01",
        "authority_name": "Department of Tribal Affairs & Hills (TAH), Government of Manipur",
        "portal_url": "https://tahmanipur.gov.in",
        "domain_type": "MANIPUR_STATE_DEPARTMENT",
        "schemes_covered": ["Post-Matric ST Manipur", "Pre-Matric ST Manipur"],
        "update_cadence": "Monthly / Seasonal Notifications",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-MN-02",
        "authority_name": "Directorate for Welfare of OBC & SC, Government of Manipur",
        "portal_url": "https://manipurobcsc.mn.gov.in",
        "domain_type": "MANIPUR_STATE_DIRECTORATE",
        "schemes_covered": [
            "Post-Matric OBC Manipur",
            "Post-Matric SC Manipur",
            "Pre-Matric OBC Manipur",
        ],
        "update_cadence": "Seasonal / Academic Cycle Notifications",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-MN-03",
        "authority_name": "Directorate of University & Higher Education, Government of Manipur",
        "portal_url": "https://highereducationmanipur.gov.in",
        "domain_type": "MANIPUR_STATE_DIRECTORATE",
        "schemes_covered": [
            "State Merit Scholarship Manipur",
            "CMCSRS (Displaced Students)",
            "Super IAS 500",
        ],
        "update_cadence": "Bi-monthly / Press Circulars",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
    {
        "registry_id": "SRC-MN-04",
        "authority_name": "Social Welfare Department, Government of Manipur",
        "portal_url": "https://manipur.gov.in",
        "domain_type": "MANIPUR_STATE_DEPARTMENT",
        "schemes_covered": [
            "CMST (Chief Ministergi Shotharabasingi Tengbang) Disability Scholarship"
        ],
        "update_cadence": "Quarterly",
        "robots_txt_status": "COMPLIANT_PUBLIC_ONLY",
        "verified_at": "2026-11-04",
    },
]


class SourceRegistryService:
    """Provides access to verified government source portal metadata."""

    @staticmethod
    def get_all_sources() -> SourceRegistryResponse:
        """Retrieve complete list of audited official portals."""
        items = [SourceRegistryItem(**src) for src in OFFICIAL_SOURCES]
        return SourceRegistryResponse(
            total_sources=len(items),
            sources=items,
        )
