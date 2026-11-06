"""Idempotent Seed Data for Verified Manipur Pilot Scholarship Schemes.

All scheme specifications, rules, income ceilings, and portal URLs are derived
strictly from official government gazettes, circulars, and M0 candidate inventory:
- Higher Education Manipur: https://highereducationmanipur.gov.in
- Tribal Affairs & Hills Manipur: https://tahmanipur.gov.in
- Directorate of OBC & SC Manipur: https://manipurobcsc.mn.gov.in
- National Scholarship Portal: https://scholarships.gov.in
Zero synthetic or hallucinated schemes.
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.modules.catalog.domain.enums import (
    DocumentLifecycleState,
    PortalType,
    PortalWindowStatus,
    SchemeLevel,
    VerificationStatus,
)
from src.modules.catalog.domain.models import (
    Scheme,
    SchemeApplicationWindow,
    SchemeBenefit,
    SchemeEligibilityRule,
    SchemeVersion,
)

logger = get_logger(__name__)

VERIFIED_PILOT_SCHEMES: list[dict[str, Any]] = [
    {
        "scheme_id": "SCH-MN-001",
        "official_code": "MN-HE-MERIT",
        "title_en": "State Merit Scholarship Manipur",
        "title_hi": "मणिपुर राज्य योग्यता छात्रवृत्ति",
        "title_mni_beng": "ꯁ꯭ꯇꯦꯠ ꯃꯦꯔꯤꯠ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ ꯃꯅꯤꯄꯨꯔ",
        "title_mni_latn": "State Merit Scholarship Manipur",
        "issuing_level": SchemeLevel.STATE_SECTOR,
        "ministry_or_department": "Directorate of University & Higher Education, Government of Manipur",
        "implementing_agency": "Higher Education Department Manipur",
        "canonical_source_url": "https://highereducationmanipur.gov.in",
        "guidelines_document_url": "https://scholarships.gov.in/public/schemeGuidelines/Manipur_state_scheme/manipur_Guidelines_3056.pdf",
        "version": {
            "version_number": 1,
            "academic_year": "2024-2025",
            "guideline_publication_date": date(2023, 8, 1),
            "content_sha256": "9596807e57debb7b141d18815054363e130a4e7cd454f5bea58598a6ce7ae22c",
            "storage_path": "documents/95/9596807e57debb7b141d18815054363e130a4e7cd454f5bea58598a6ce7ae22c.pdf",
            "verification_status": VerificationStatus.OFFICIAL_VERIFIED,
            "verified_by_user_id": "m0_statutory_auditor",
            "verification_notes": "Verified against Higher Education Manipur official circular August 2023.",
        },
        "rule": {
            "income_ceiling_annual_inr": 450000.00,
            "minimum_qualifying_marks_percent": 60.00,
            "target_categories": ["ALL"],
            "eligible_domiciles": ["MANIPUR"],
            "eligible_course_levels": ["UNDERGRADUATE", "POSTGRADUATE"],
            "eligible_genders": ["ANY"],
            "ast_rule_logic": {
                "and": [
                    {"<=": [{"var": "annual_family_income_inr"}, 450000]},
                    {">=": [{"var": "marks_percent"}, 60.0]},
                    {"in": [{"var": "domicile_state"}, ["MANIPUR"]]},
                    {"in": [{"var": "course_level"}, ["UNDERGRADUATE", "POSTGRADUATE"]]},
                ]
            },
            "rule_description_en": "Family income <= ₹4,50,000, Marks >= 60%, Domicile Manipur, Course UG or PG.",
        },
        "window": {
            "portal_type": PortalType.NSP_2_0,
            "portal_url": "https://scholarships.gov.in",
            "portal_status": PortalWindowStatus.OPEN,
            "window_open_date": date(2024, 7, 1),
            "window_close_date": date(2024, 11, 30),
            "requires_otr_face_rd": True,
        },
        "benefit": {
            "tuition_fee_coverage_desc": "Up to ₹7,500 annual merit stipend disbursed via PFMS.",
            "disbursement_mechanism": "DBT_PFMS",
            "benefit_summary_en": "Up to ₹7,500 per annum disbursed via Direct Benefit Transfer (PFMS).",
        },
    },
    {
        "scheme_id": "SCH-MN-005",
        "official_code": "MN-ST-POST",
        "title_en": "Post-Matric Scholarship for ST Students - Manipur",
        "title_hi": "अनुसूचित जनजाति के छात्रों के लिए मैट्रिक-उपरांत छात्रवृत्ति - मणिपुर",
        "title_mni_beng": "ꯑꯦꯁ.ꯇꯤ. ꯃꯆꯥꯁꯤꯡꯒꯤ ꯃꯦꯠꯔꯤꯛ ꯃꯇꯨꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ - ꯃꯅꯤꯄꯨꯔ",
        "title_mni_latn": "Post-Matric Scholarship for ST Students - Manipur",
        "issuing_level": SchemeLevel.CENTRALLY_SPONSORED,
        "ministry_or_department": "Department of Tribal Affairs & Hills, Government of Manipur",
        "implementing_agency": "Tribal Affairs & Hills Department Manipur / Ministry of Tribal Affairs",
        "canonical_source_url": "https://tahmanipur.gov.in",
        "guidelines_document_url": "https://scholarships.gov.in/public/schemeGuidelines/EDUPostMatricScholarshipPMSforSTstudents.pdf",
        "version": {
            "version_number": 1,
            "academic_year": "2024-2025",
            "guideline_publication_date": date(2022, 6, 1),
            "content_sha256": "eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe",
            "storage_path": "documents/eb/eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe.pdf",
            "verification_status": VerificationStatus.OFFICIAL_VERIFIED,
            "verified_by_user_id": "m0_statutory_auditor",
            "verification_notes": "Verified against MoTA Centrally Sponsored Scheme Guidelines 2022.",
        },
        "rule": {
            "income_ceiling_annual_inr": 250000.00,
            "minimum_qualifying_marks_percent": None,
            "target_categories": ["ST"],
            "eligible_domiciles": ["MANIPUR"],
            "eligible_course_levels": [
                "POST_MATRIC",
                "UNDERGRADUATE",
                "POSTGRADUATE",
                "DIPLOMA",
            ],
            "eligible_genders": ["ANY"],
            "ast_rule_logic": {
                "and": [
                    {"<=": [{"var": "annual_family_income_inr"}, 250000]},
                    {"in": [{"var": "social_category"}, ["ST"]]},
                    {"in": [{"var": "domicile_state"}, ["MANIPUR"]]},
                    {
                        "in": [
                            {"var": "course_level"},
                            ["POST_MATRIC", "UNDERGRADUATE", "POSTGRADUATE", "DIPLOMA"],
                        ]
                    },
                ]
            },
            "rule_description_en": "Family income <= ₹2,50,000, Category ST, Domicile Manipur, Post-Matric course.",
        },
        "window": {
            "portal_type": PortalType.NSP_2_0,
            "portal_url": "https://scholarships.gov.in",
            "portal_status": PortalWindowStatus.OPEN,
            "window_open_date": date(2024, 7, 1),
            "window_close_date": date(2024, 11, 30),
            "requires_otr_face_rd": True,
        },
        "benefit": {
            "maintenance_allowance_day_scholar_annual_inr": 7000.00,
            "maintenance_allowance_hosteller_annual_inr": 13500.00,
            "tuition_fee_coverage_desc": "Compulsory non-refundable course fee reimbursement.",
            "disbursement_mechanism": "DBT_PFMS",
            "benefit_summary_en": "Compulsory fee reimbursement plus maintenance allowance up to ₹13,500/year.",
        },
    },
    {
        "scheme_id": "SCH-MN-007",
        "official_code": "MN-OBC-POST",
        "title_en": "Post-Matric Scholarship for OBC Students - Manipur",
        "title_hi": "अन्य पिछड़ा वर्ग के छात्रों के लिए मैट्रिक-उपरांत छात्रवृत्ति - मणिपुर",
        "title_mni_beng": "ꯑꯣ.ꯕꯤ.ꯁꯤ. ꯃꯆꯥꯁꯤꯡꯒꯤ ꯃꯦꯠꯔꯤꯛ ꯃꯇꯨꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ - ꯃꯅꯤꯄꯨꯔ",
        "title_mni_latn": "Post-Matric Scholarship for OBC Students - Manipur",
        "issuing_level": SchemeLevel.CENTRALLY_SPONSORED,
        "ministry_or_department": "Directorate for Welfare of OBC & SC, Government of Manipur",
        "implementing_agency": "Directorate for Welfare of OBC & SC / MoSJE",
        "canonical_source_url": "https://manipurobcsc.mn.gov.in",
        "guidelines_document_url": "https://scholarships.gov.in/public/schemeGuidelines/Centrally%20Sponsored%20Scheme%20of%20Post%20Matric%20Scholarship%20Scheme%20for%20OBC_scheme.pdf",
        "version": {
            "version_number": 1,
            "academic_year": "2024-2025",
            "guideline_publication_date": date(2023, 7, 1),
            "content_sha256": "3e7cea65397d06b42644681257beea11193aff243a5aa398818f6f2c2dbfdaf5",
            "storage_path": "documents/3e/3e7cea65397d06b42644681257beea11193aff243a5aa398818f6f2c2dbfdaf5.pdf",
            "verification_status": VerificationStatus.OFFICIAL_VERIFIED,
            "verified_by_user_id": "m0_statutory_auditor",
            "verification_notes": "Verified against PM-YASASVI OBC Post-Matric Framework July 2023.",
        },
        "rule": {
            "income_ceiling_annual_inr": 250000.00,
            "minimum_qualifying_marks_percent": None,
            "target_categories": ["OBC"],
            "eligible_domiciles": ["MANIPUR"],
            "eligible_course_levels": [
                "POST_MATRIC",
                "UNDERGRADUATE",
                "POSTGRADUATE",
                "DIPLOMA",
            ],
            "eligible_genders": ["ANY"],
            "ast_rule_logic": {
                "and": [
                    {"<=": [{"var": "annual_family_income_inr"}, 250000]},
                    {"in": [{"var": "social_category"}, ["OBC"]]},
                    {"in": [{"var": "domicile_state"}, ["MANIPUR"]]},
                    {
                        "in": [
                            {"var": "course_level"},
                            ["POST_MATRIC", "UNDERGRADUATE", "POSTGRADUATE", "DIPLOMA"],
                        ]
                    },
                ]
            },
            "rule_description_en": "Family income <= ₹2,50,000, Category OBC, Domicile Manipur, Post-Matric course.",
        },
        "window": {
            "portal_type": PortalType.NSP_2_0,
            "portal_url": "https://scholarships.gov.in",
            "portal_status": PortalWindowStatus.OPEN,
            "window_open_date": date(2024, 7, 1),
            "window_close_date": date(2024, 11, 30),
            "requires_otr_face_rd": True,
        },
        "benefit": {
            "maintenance_allowance_day_scholar_annual_inr": 10000.00,
            "maintenance_allowance_hosteller_annual_inr": 20000.00,
            "tuition_fee_coverage_desc": "Tuition fee reimbursement under PM-YASASVI.",
            "disbursement_mechanism": "DBT_PFMS",
            "benefit_summary_en": "Tuition fee reimbursement and maintenance allowance up to ₹20,000 per annum.",
        },
    },
    {
        "scheme_id": "SCH-MN-009",
        "official_code": "MN-SC-POST",
        "title_en": "Post-Matric Scholarship for SC Students - Manipur",
        "title_hi": "अनुसूचित जाति के छात्रों के लिए मैट्रिक-उपरांत छात्रवृत्ति - मणिपुर",
        "title_mni_beng": "ꯑꯦꯁ.ꯁꯤ. ꯃꯆꯥꯁꯤꯡꯒꯤ ꯃꯦꯠꯔꯤꯛ ꯃꯇꯨꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ - ꯃꯅꯤꯄꯨꯔ",
        "title_mni_latn": "Post-Matric Scholarship for SC Students - Manipur",
        "issuing_level": SchemeLevel.CENTRALLY_SPONSORED,
        "ministry_or_department": "Directorate for Welfare of OBC & SC, Government of Manipur",
        "implementing_agency": "Directorate for Welfare of OBC & SC / MoSJE",
        "canonical_source_url": "https://manipurobcsc.mn.gov.in",
        "guidelines_document_url": "https://scholarships.gov.in/public/schemeGuidelines/Postmatric_SC.pdf",
        "version": {
            "version_number": 1,
            "academic_year": "2024-2025",
            "guideline_publication_date": date(2021, 1, 1),
            "content_sha256": "cf73697baff4d7ebaf5919363296479b501ea9efc146a27de50623a9472cfa57",
            "storage_path": "documents/cf/cf73697baff4d7ebaf5919363296479b501ea9efc146a27de50623a9472cfa57.pdf",
            "verification_status": VerificationStatus.OFFICIAL_VERIFIED,
            "verified_by_user_id": "m0_statutory_auditor",
            "verification_notes": "Verified against Revised Centrally Sponsored SC Post-Matric Scheme 2021.",
        },
        "rule": {
            "income_ceiling_annual_inr": 250000.00,
            "minimum_qualifying_marks_percent": None,
            "target_categories": ["SC"],
            "eligible_domiciles": ["MANIPUR"],
            "eligible_course_levels": [
                "POST_MATRIC",
                "UNDERGRADUATE",
                "POSTGRADUATE",
                "DIPLOMA",
            ],
            "eligible_genders": ["ANY"],
            "ast_rule_logic": {
                "and": [
                    {"<=": [{"var": "annual_family_income_inr"}, 250000]},
                    {"in": [{"var": "social_category"}, ["SC"]]},
                    {"in": [{"var": "domicile_state"}, ["MANIPUR"]]},
                    {
                        "in": [
                            {"var": "course_level"},
                            ["POST_MATRIC", "UNDERGRADUATE", "POSTGRADUATE", "DIPLOMA"],
                        ]
                    },
                ]
            },
            "rule_description_en": "Family income <= ₹2,50,000, Category SC, Domicile Manipur, Post-Matric course.",
        },
        "window": {
            "portal_type": PortalType.NSP_2_0,
            "portal_url": "https://scholarships.gov.in",
            "portal_status": PortalWindowStatus.OPEN,
            "window_open_date": date(2024, 7, 1),
            "window_close_date": date(2024, 11, 30),
            "requires_otr_face_rd": True,
            "requires_freeship_card": True,
        },
        "benefit": {
            "maintenance_allowance_day_scholar_annual_inr": 7000.00,
            "maintenance_allowance_hosteller_annual_inr": 13500.00,
            "tuition_fee_coverage_desc": "Full non-refundable fee coverage with Freeship Card upfront waiver.",
            "disbursement_mechanism": "DBT_PFMS",
            "benefit_summary_en": "Full fee coverage + maintenance allowance up to ₹13,500/year; Freeship Card eligible.",
        },
    },
    {
        "scheme_id": "SCH-MN-006",
        "official_code": "MN-ST-PRE",
        "title_en": "Pre-Matric Scholarship for ST Students (Classes IX & X) - Manipur",
        "title_hi": "अनुसूचित जनजाति के छात्रों के लिए मैट्रिक-पूर्व छात्रवृत्ति (कक्षा IX और X) - मणिपुर",
        "title_mni_beng": "ꯑꯦꯁ.ꯇꯤ. ꯃꯆꯥꯁꯤꯡꯒꯤ ꯃꯦꯠꯔꯤꯛ ꯃꯃꯥꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ - ꯃꯅꯤꯄꯨꯔ",
        "title_mni_latn": "Pre-Matric Scholarship for ST Students (Classes IX & X) - Manipur",
        "issuing_level": SchemeLevel.CENTRALLY_SPONSORED,
        "ministry_or_department": "Department of Tribal Affairs & Hills, Government of Manipur",
        "implementing_agency": "Tribal Affairs & Hills Department Manipur",
        "canonical_source_url": "https://tahmanipur.gov.in",
        "guidelines_document_url": "https://scholarships.gov.in/public/schemeGuidelines/guidelines-Pre-matric-ST.pdf",
        "version": {
            "version_number": 1,
            "academic_year": "2024-2025",
            "guideline_publication_date": date(2022, 6, 1),
            "content_sha256": "8e35745e3319bfe532502d9c28e49d6ce704ec1a95a87bd7e983631b1a99474b",
            "storage_path": "documents/8e/8e35745e3319bfe532502d9c28e49d6ce704ec1a95a87bd7e983631b1a99474b.pdf",
            "verification_status": VerificationStatus.OFFICIAL_VERIFIED,
            "verified_by_user_id": "m0_statutory_auditor",
            "verification_notes": "Verified against Revised 2022 CSS MoTA Guidelines for Pre-Matric ST.",
        },
        "rule": {
            "income_ceiling_annual_inr": 250000.00,
            "minimum_qualifying_marks_percent": None,
            "target_categories": ["ST"],
            "eligible_domiciles": ["MANIPUR"],
            "eligible_course_levels": ["CLASS_9_10"],
            "eligible_genders": ["ANY"],
            "ast_rule_logic": {
                "and": [
                    {"<=": [{"var": "annual_family_income_inr"}, 250000]},
                    {"in": [{"var": "social_category"}, ["ST"]]},
                    {"in": [{"var": "domicile_state"}, ["MANIPUR"]]},
                    {"in": [{"var": "course_level"}, ["CLASS_9_10"]]},
                ]
            },
            "rule_description_en": "Family income <= ₹2,50,000, Category ST, Domicile Manipur, Classes 9-10.",
        },
        "window": {
            "portal_type": PortalType.NSP_2_0,
            "portal_url": "https://scholarships.gov.in",
            "portal_status": PortalWindowStatus.CLOSED,
            "window_open_date": date(2024, 7, 1),
            "window_close_date": date(2024, 10, 31),
            "requires_otr_face_rd": True,
        },
        "benefit": {
            "maintenance_allowance_day_scholar_annual_inr": 3500.00,
            "maintenance_allowance_hosteller_annual_inr": 7000.00,
            "book_and_equipment_grant_annual_inr": 1000.00,
            "tuition_fee_coverage_desc": "Maintenance and academic book allowances for secondary school students.",
            "disbursement_mechanism": "DBT_PFMS",
            "benefit_summary_en": "Maintenance allowance of ₹3,500 (day scholar) or ₹7,000 (hosteller) + ₹1,000 book grant.",
        },
    },
    {
        "scheme_id": "SCH-MN-003",
        "official_code": "MN-HE-CMCSRS",
        "title_en": "Chief Minister’s College Students Rehabilitation Scheme (CMCSRS)",
        "title_hi": "मुख्यमंत्री कॉलेज छात्र पुनर्वास योजना - मणिपुर",
        "title_mni_beng": "ꯆꯤꯐ ꯃꯤꯅꯤꯁ꯭ꯇꯔꯒꯤ ꯀꯣꯂꯦꯖ ꯃꯆꯥꯁꯤꯡꯒꯤ ꯔꯤꯍꯦꯕꯤꯂꯤꯇꯦꯁꯟ ꯁ꯭ꯀꯤꯝ",
        "title_mni_latn": "Chief Minister’s College Students Rehabilitation Scheme (CMCSRS)",
        "issuing_level": SchemeLevel.STATE_SECTOR,
        "ministry_or_department": "Directorate of University & Higher Education, Government of Manipur",
        "implementing_agency": "Higher Education Department Manipur",
        "canonical_source_url": "https://highereducationmanipur.gov.in",
        "guidelines_document_url": "https://highereducationmanipur.gov.in/chief-ministers-college-students-rehabilitation-scheme-cmcsrs-2023/",
        "version": {
            "version_number": 1,
            "academic_year": "2024-2025",
            "guideline_publication_date": date(2023, 7, 1),
            "content_sha256": "8d1949278ec951864b7f21fbc171f8afa99fdb4dcb2bc767e3b18a81d3ae7ff8",
            "storage_path": "documents/8d/8d1949278ec951864b7f21fbc171f8afa99fdb4dcb2bc767e3b18a81d3ae7ff8.pdf",
            "verification_status": VerificationStatus.OFFICIAL_VERIFIED,
            "verified_by_user_id": "m0_statutory_auditor",
            "verification_notes": "Verified against Higher Education Manipur Notification July 2023 for displaced students.",
        },
        "rule": {
            "income_ceiling_annual_inr": None,
            "minimum_qualifying_marks_percent": None,
            "target_categories": ["ALL"],
            "eligible_domiciles": ["MANIPUR"],
            "eligible_course_levels": ["UNDERGRADUATE"],
            "eligible_genders": ["ANY"],
            "ast_rule_logic": {
                "and": [
                    {"==": [{"var": "is_displaced"}, True]},
                    {"in": [{"var": "domicile_state"}, ["MANIPUR"]]},
                    {"in": [{"var": "course_level"}, ["UNDERGRADUATE"]]},
                ]
            },
            "rule_description_en": "Displaced undergraduate college student of Manipur.",
        },
        "window": {
            "portal_type": PortalType.STATE_DIRECT_PORTAL,
            "portal_url": "https://highereducationmanipur.gov.in",
            "portal_status": PortalWindowStatus.OPEN,
            "window_open_date": date(2024, 7, 1),
            "window_close_date": date(2025, 3, 31),
        },
        "benefit": {
            "tuition_fee_coverage_desc": "100% full tuition and college admission fee waiver with free college transfer.",
            "book_and_equipment_grant_annual_inr": 10000.00,
            "disbursement_mechanism": "DIRECT_INSTITUTE_AND_DBT",
            "benefit_summary_en": "Tuition fee waiver, free college transfer, and ₹10,000 rehabilitation grant.",
        },
    },
]


async def seed_pilot_schemes(session: AsyncSession) -> int:
    """Idempotently seed verified Manipur scholarship schemes into catalog."""
    seeded_count = 0
    for data in VERIFIED_PILOT_SCHEMES:
        scheme_id = data["scheme_id"]
        # Check existing scheme
        stmt = select(Scheme).where(Scheme.scheme_id == scheme_id)
        res = await session.execute(stmt)
        scheme = res.scalars().first()

        if not scheme:
            scheme = Scheme(
                scheme_id=scheme_id,
                official_code=data["official_code"],
                title_en=data["title_en"],
                title_hi=data["title_hi"],
                title_mni_beng=data["title_mni_beng"],
                title_mni_latn=data["title_mni_latn"],
                issuing_level=data["issuing_level"],
                ministry_or_department=data["ministry_or_department"],
                implementing_agency=data["implementing_agency"],
                canonical_source_url=data["canonical_source_url"],
                guidelines_document_url=data["guidelines_document_url"],
                is_active=True,
            )
            session.add(scheme)
            await session.flush()
            seeded_count += 1

            # Add Version 1
            ver_data = data["version"]
            version = SchemeVersion(
                version_id=uuid.uuid4(),
                scheme_id=scheme_id,
                version_number=ver_data["version_number"],
                academic_year=ver_data["academic_year"],
                guideline_publication_date=ver_data["guideline_publication_date"],
                content_sha256=ver_data["content_sha256"],
                storage_path=ver_data.get("storage_path"),
                lifecycle_state=DocumentLifecycleState.STORED.value,
                verification_status=ver_data["verification_status"],
                verified_by_user_id=ver_data["verified_by_user_id"],
                verification_notes=ver_data["verification_notes"],
            )
            session.add(version)
            await session.flush()

            # Add Eligibility Rule
            rule_data = data["rule"]
            rule = SchemeEligibilityRule(
                rule_id=uuid.uuid4(),
                version_id=version.version_id,
                income_ceiling_annual_inr=rule_data["income_ceiling_annual_inr"],
                minimum_qualifying_marks_percent=rule_data["minimum_qualifying_marks_percent"],
                target_categories=rule_data["target_categories"],
                eligible_domiciles=rule_data["eligible_domiciles"],
                eligible_course_levels=rule_data["eligible_course_levels"],
                eligible_genders=rule_data["eligible_genders"],
                ast_rule_logic=rule_data["ast_rule_logic"],
                rule_description_en=rule_data["rule_description_en"],
            )
            session.add(rule)

            # Add Application Window
            win_data = data["window"]
            window = SchemeApplicationWindow(
                window_id=uuid.uuid4(),
                version_id=version.version_id,
                portal_type=win_data["portal_type"],
                portal_url=win_data["portal_url"],
                portal_status=win_data["portal_status"],
                window_open_date=win_data.get("window_open_date"),
                window_close_date=win_data.get("window_close_date"),
                requires_otr_face_rd=win_data.get("requires_otr_face_rd", False),
                requires_freeship_card=win_data.get("requires_freeship_card", False),
            )
            session.add(window)

            # Add Benefit
            ben_data = data["benefit"]
            benefit = SchemeBenefit(
                benefit_id=uuid.uuid4(),
                version_id=version.version_id,
                maintenance_allowance_day_scholar_annual_inr=ben_data.get(
                    "maintenance_allowance_day_scholar_annual_inr"
                ),
                maintenance_allowance_hosteller_annual_inr=ben_data.get(
                    "maintenance_allowance_hosteller_annual_inr"
                ),
                tuition_fee_coverage_desc=ben_data["tuition_fee_coverage_desc"],
                book_and_equipment_grant_annual_inr=ben_data.get(
                    "book_and_equipment_grant_annual_inr"
                ),
                disbursement_mechanism=ben_data.get("disbursement_mechanism", "DBT_PFMS"),
                benefit_summary_en=ben_data["benefit_summary_en"],
            )
            session.add(benefit)

    await session.commit()
    logger.info("Seeded %d verified Manipur pilot schemes into catalog.", seeded_count)
    return seeded_count
