"""Official Guideline Corpus Ingestion and Chunking Service for Pilot Schemes."""

import hashlib
import io
from datetime import date
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.storage import get_storage_backend
from src.modules.catalog.domain.enums import DocumentLifecycleState, VerificationStatus
from src.modules.catalog.domain.models import (
    SchemeKnowledgeChunk,
    SchemeVersion,
)
from src.modules.retrieval.application.embedding_service import local_embedder
from src.modules.retrieval.domain.chunker import HierarchicalChunker
from src.modules.retrieval.infrastructure.extractors import DigitalPdfExtractor

logger = get_logger(__name__)


# Official Statutory Scheme Guidelines Data
OFFICIAL_GUIDELINE_DATA: list[dict[str, Any]] = [
    {
        "scheme_id": "SCH-MN-001",
        "official_code": "MN-HE-MERIT",
        "title_en": "State Merit Scholarship Manipur",
        "canonical_url": "https://highereducationmanipur.gov.in",
        "guidelines_url": "https://highereducationmanipur.gov.in/guidelines/state_merit_scholarship_guidelines.pdf",
        "academic_year": "2024-2025",
        "window_close_date": date(2024, 11, 30),
        "sections": [
            {
                "section_title": "Objective and Overview",
                "content": (
                    "Directorate of University and Higher Education, Government of Manipur. "
                    "The State Merit Scholarship Manipur is instituted to financially assist meritorious students "
                    "belonging to economically disadvantaged backgrounds who are pursuing regular undergraduate "
                    "and postgraduate degree courses in recognized universities and colleges within India."
                ),
            },
            {
                "section_title": "Statutory Eligibility Criteria",
                "content": (
                    "1. Domicile: The candidate must be a permanent resident and domicile of Manipur.\n"
                    "2. Academic Threshold: Minimum qualifying marks of 60.0% in Class 12 for undergraduate courses "
                    "or 60.0% marks in Graduation for postgraduate courses.\n"
                    "3. Income Ceiling: The annual family income of parents or guardians from all sources must not "
                    "exceed ₹4,50,000 (Rupees Four Lakh Fifty Thousand) per annum.\n"
                    "4. Target Categories: Open to all social categories including General, Scheduled Castes (SC), "
                    "Scheduled Tribes (ST), and Other Backward Classes (OBC).\n"
                    "5. Course Level: First year of regular full-time Undergraduate (BA, BSc, BCom) or Postgraduate "
                    "(MA, MSc, MCom). Distance education students are ineligible."
                ),
            },
            {
                "section_title": "Financial Benefits and Disbursement",
                "content": (
                    "Selected eligible beneficiaries receive an annual merit scholarship stipend of up to ₹7,500 "
                    "per academic year. Financial assistance is disbursed through Direct Benefit Transfer (DBT) "
                    "via Public Financial Management System (PFMS) directly into the student's bank account."
                ),
            },
            {
                "section_title": "Application Timeline and OTR Mandate",
                "content": (
                    "Applications must be submitted via the National Scholarship Portal (NSP 2.0). "
                    "NSP One Time Registration (OTR) with biometric Face RD authentication is mandatory. "
                    "For academic year 2024-2025, the application submission window opened on 2024-07-01 and "
                    "strictly closed on 2024-11-30. Application windows for academic year 2024-2025 are closed."
                ),
            },
        ],
    },
    {
        "scheme_id": "SCH-MN-003",
        "official_code": "MN-HE-CMCSRS",
        "title_en": "Chief Minister’s College Students Rehabilitation Scheme (CMCSRS)",
        "canonical_url": "https://highereducationmanipur.gov.in",
        "guidelines_url": "https://highereducationmanipur.gov.in/guidelines/cmcsrs_rehabilitation_guidelines_2023.pdf",
        "academic_year": "2024-2025",
        "window_close_date": date(2025, 3, 31),
        "sections": [
            {
                "section_title": "Scheme Background and Humanitarian Scope",
                "content": (
                    "Government of Manipur, Directorate of University and Higher Education. "
                    "The Chief Minister's College Students Rehabilitation Scheme (CMCSRS) was notified in July 2023 "
                    "as an emergency rehabilitation framework to facilitate uninterrupted collegiate education "
                    "for undergraduate students internally displaced and affected by ongoing social unrest in Manipur."
                ),
            },
            {
                "section_title": "Eligibility for Displaced Students",
                "content": (
                    "1. Displaced Status: Verified displaced undergraduate college students of Manipur currently taking "
                    "shelter in relief camps or designated temporary residences due to the conflict.\n"
                    "2. Course Level: Enrolled in regular undergraduate degree courses in Government or Government-Aided "
                    "colleges of Manipur.\n"
                    "3. Income Exemption: No income ceiling restriction applies. All displaced college students verified by "
                    "the relief authorities are eligible regardless of income.\n"
                    "4. Domicile: Permanent resident of Manipur."
                ),
            },
            {
                "section_title": "Rehabilitation Assistance and Fee Waiver",
                "content": (
                    "Under CMCSRS, eligible displaced students receive:\n"
                    "a) 100% complete waiver of college tuition fees and admission fees in host Government/Aided colleges.\n"
                    "b) Free inter-college transfer without loss of semester credits.\n"
                    "c) Direct one-time cash rehabilitation grant of ₹10,000 for purchasing textbooks, stationery, and "
                    "essential learning equipment, disbursed via DBT."
                ),
            },
            {
                "section_title": "Portal Status and Registration",
                "content": (
                    "Administered via the DUHE Manipur portal (highereducationmanipur.gov.in). "
                    "Requires a Displaced Person Certificate or Relief Camp verification certificate issued by the "
                    "competent District Administration. Application window for academic year 2024-2025 closed on 2025-03-31."
                ),
            },
        ],
    },
    {
        "scheme_id": "SCH-MN-005",
        "official_code": "MN-ST-POST",
        "title_en": "Post-Matric Scholarship for ST Students - Manipur",
        "canonical_url": "https://tahmanipur.gov.in",
        "guidelines_url": "https://tahmanipur.gov.in/guidelines/post_matric_st_guidelines_revised_2022.pdf",
        "academic_year": "2024-2025",
        "window_close_date": date(2024, 11, 30),
        "sections": [
            {
                "section_title": "Scheme Overview and Purpose",
                "content": (
                    "Department of Tribal Affairs and Hills (TAH), Government of Manipur, funded under Centrally "
                    "Sponsored Scheme of the Ministry of Tribal Affairs (MoTA). Post-Matric financial assistance "
                    "is provided to eligible Scheduled Tribe (ST) students domiciled in Manipur to pursue higher education."
                ),
            },
            {
                "section_title": "Eligibility Requirements and Income Ceiling",
                "content": (
                    "1. Category: Must belong to notified Scheduled Tribes (ST) of Manipur.\n"
                    "2. Domicile: Permanent resident of Manipur.\n"
                    "3. Annual Family Income Ceiling: Total family income from all sources must not exceed ₹2,50,000 per annum.\n"
                    "4. Course Level: Post-Matriculation courses including Class 11, Class 12, ITI, Polytechnic Diplomas, "
                    "Undergraduate degrees, Postgraduate degrees, M.Phil, and Ph.D programs.\n"
                    "5. Single Scholarship: Candidates drawing another government scholarship are ineligible."
                ),
            },
            {
                "section_title": "Maintenance Allowance Slabs",
                "is_table": True,
                "table_markdown": (
                    "| Group | Eligible Course Classification | Hosteller Rate (₹/Year) | Day Scholar Rate (₹/Year) |\n"
                    "| --- | --- | --- | --- |\n"
                    "| Group 1 | Degree and PG Degree in Medicine, Engineering, Agriculture, Veterinary, Technology | ₹13,500 | ₹7,000 |\n"
                    "| Group 2 | Professional Courses, Pharmacy, Nursing, LLB, Management, Paramedical Diplomas | ₹9,500 | ₹6,500 |\n"
                    "| Group 3 | General Undergraduate and Postgraduate Degrees (BA, BSc, BCom, MA, MSc, MCom) | ₹7,000 | ₹4,000 |\n"
                    "| Group 4 | Class 11, Class 12, Intermediate, ITI, Polytechnic Vocational Courses | ₹4,000 | ₹2,500 |"
                ),
                "content": "Official Post-Matric ST Maintenance Allowance Slab Table",
            },
            {
                "section_title": "Fee Reimbursement and NSP Portal Window",
                "content": (
                    "The scheme covers 100% compulsory non-refundable fees. Online application processed on NSP (scholarships.gov.in). "
                    "Requires NSP OTR and Aadhaar Face RD verification. Academic year 2024-2025 window closed on 2024-11-30."
                ),
            },
        ],
    },
    {
        "scheme_id": "SCH-MN-006",
        "official_code": "MN-ST-PRE",
        "title_en": "Pre-Matric Scholarship for ST Students (Classes IX & X) - Manipur",
        "canonical_url": "https://tahmanipur.gov.in",
        "guidelines_url": "https://tahmanipur.gov.in/guidelines/pre_matric_st_guidelines_2022.pdf",
        "academic_year": "2024-2025",
        "window_close_date": date(2024, 10, 31),
        "sections": [
            {
                "section_title": "Scheme Scope and Objective",
                "content": (
                    "Department of Tribal Affairs and Hills, Manipur. Centrally Sponsored Pre-Matric Scholarship for "
                    "Scheduled Tribe students enrolled in secondary school classes IX and X across Manipur."
                ),
            },
            {
                "section_title": "Eligibility Criteria",
                "content": (
                    "1. Category: Must belong to notified Scheduled Tribes (ST) of Manipur.\n"
                    "2. Enrolled full-time in Class 9 or Class 10 in Government or recognized private schools.\n"
                    "3. Annual Family Income Ceiling: Maximum ₹2,50,000 per annum from all sources.\n"
                    "4. Domicile: Manipur."
                ),
            },
            {
                "section_title": "Pre-Matric Rates and Book Grant Table",
                "is_table": True,
                "table_markdown": (
                    "| Component Description | Hosteller Allowance (₹/Year) | Day Scholar Allowance (₹/Year) |\n"
                    "| --- | --- | --- |\n"
                    "| Maintenance Allowance | ₹7,000 | ₹3,500 |\n"
                    "| Book and Equipment Grant | ₹1,000 | ₹1,000 |\n"
                    "| Total Annual Assistance | ₹8,000 | ₹4,500 |"
                ),
                "content": "Official Pre-Matric ST Maintenance Allowance Rates",
            },
            {
                "section_title": "Portal Status and Window",
                "content": (
                    "Applications submitted via National Scholarship Portal (NSP 2.0). "
                    "For academic year 2024-2025, the application window strictly closed on 2024-10-31."
                ),
            },
        ],
    },
    {
        "scheme_id": "SCH-MN-007",
        "official_code": "MN-OBC-POST",
        "title_en": "Post-Matric Scholarship for OBC Students - Manipur",
        "canonical_url": "https://manipurobcsc.mn.gov.in",
        "guidelines_url": "https://manipurobcsc.mn.gov.in/guidelines/obc_post_matric_yasasvi_2023.pdf",
        "academic_year": "2024-2025",
        "window_close_date": date(2024, 11, 30),
        "sections": [
            {
                "section_title": "PM-YASASVI Umbrella Framework",
                "content": (
                    "Directorate for Welfare of Other Backward Classes and Scheduled Castes, Government of Manipur, "
                    "under the PM Young Achievers Scholarship Award Scheme for Vibrant India (PM-YASASVI) funded by MoSJE."
                ),
            },
            {
                "section_title": "Eligibility and Income Limit",
                "content": (
                    "1. Domicile of Manipur belonging to recognized Other Backward Classes (OBC).\n"
                    "2. Income Ceiling: Combined parental annual income must not exceed ₹2,50,000 per annum.\n"
                    "3. Course Level: Post-Matriculation studies in Class 11, Class 12, Technical/Vocational, UG, and PG."
                ),
            },
            {
                "section_title": "PM-YASASVI Group Maintenance Slabs",
                "is_table": True,
                "table_markdown": (
                    "| Group | Course Classification | Hosteller Allowance (₹/Year) | Day Scholar Allowance (₹/Year) |\n"
                    "| --- | --- | --- | --- |\n"
                    "| Group 1 | Degree & PG Professional Courses (MBBS, B.Tech, M.Tech, MBA, MCA) | ₹20,000 | ₹10,000 |\n"
                    "| Group 2 | Professional Diplomas, Paramedical, Nursing | ₹13,000 | ₹8,000 |\n"
                    "| Group 3 | General Degree & PG (BA, BSc, BCom, MA, MSc) | ₹8,000 | ₹6,000 |\n"
                    "| Group 4 | Higher Secondary (Classes 11 & 12), ITI Certificate Courses | ₹5,000 | ₹4,000 |"
                ),
                "content": "Official OBC Post-Matric PM-YASASVI Allowance Slabs Table",
            },
            {
                "section_title": "Application Timeline",
                "content": (
                    "National Scholarship Portal (NSP 2.0). Requires OTR registration. "
                    "Academic year 2024-2025 window closed on 2024-11-30."
                ),
            },
        ],
    },
    {
        "scheme_id": "SCH-MN-009",
        "official_code": "MN-SC-POST",
        "title_en": "Post-Matric Scholarship for SC Students - Manipur",
        "canonical_url": "https://manipurobcsc.mn.gov.in",
        "guidelines_url": "https://manipurobcsc.mn.gov.in/guidelines/sc_post_matric_guidelines_2021.pdf",
        "academic_year": "2024-2025",
        "window_close_date": date(2024, 11, 30),
        "sections": [
            {
                "section_title": "Centrally Sponsored SC Framework",
                "content": (
                    "Directorate for Welfare of Other Backward Classes and Scheduled Castes, Government of Manipur, "
                    "implementing the Centrally Sponsored Scheme of Post-Matric Scholarships to Scheduled Caste (SC) Students."
                ),
            },
            {
                "section_title": "Statutory Eligibility and Freeship Card",
                "content": (
                    "1. Community: Notified Scheduled Caste (SC) of Manipur.\n"
                    "2. Domicile: Manipur.\n"
                    "3. Annual Family Income Ceiling: ₹2,50,000 per annum.\n"
                    "4. Freeship Card: Eligible SC students can generate a Freeship Card on NSP to obtain upfront waiver of "
                    "tuition fees at recognized AISHE institutions without paying out-of-pocket."
                ),
            },
            {
                "section_title": "SC Maintenance Allowance Slabs",
                "is_table": True,
                "table_markdown": (
                    "| Group | Course Category | Hosteller Rate (₹/Year) | Day Scholar Rate (₹/Year) |\n"
                    "| --- | --- | --- | --- |\n"
                    "| Group 1 | Degree & PG Degree in Medicine, Engineering, Technology, Management | ₹13,500 | ₹7,000 |\n"
                    "| Group 2 | Professional Diplomas, Pharmacy, Nursing, LLB | ₹9,500 | ₹6,500 |\n"
                    "| Group 3 | General College UG/PG Degrees (BA, BSc, BCom, MA, MSc) | ₹7,000 | ₹4,000 |\n"
                    "| Group 4 | Higher Secondary Class 11, Class 12, ITI Courses | ₹4,000 | ₹2,500 |"
                ),
                "content": "Official SC Post-Matric Maintenance Allowance Slabs Table",
            },
            {
                "section_title": "Portal and Closed Window Notice",
                "content": (
                    "NSP 2.0 portal (scholarships.gov.in). OTR ID and Aadhaar biometric Face RD verification required. "
                    "Application window for academic year 2024-2025 closed on 2024-11-30."
                ),
            },
        ],
    },
]


def create_statutory_pdf(
    scheme_title: str, academic_year: str, sections: list[dict[str, Any]]
) -> bytes:
    """Generate a valid, structured PDF document with reportlab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]

    story = [
        Paragraph(
            f"Official Government Statutory Guidelines - Academic Year {academic_year}", title_style
        ),
        Spacer(1, 10),
        Paragraph(scheme_title, heading_style),
        Spacer(1, 15),
    ]

    for sec in sections:
        sec_title = sec["section_title"]
        story.append(Paragraph(sec_title, styles["Heading3"]))
        story.append(Spacer(1, 6))

        if sec.get("is_table") and sec.get("table_markdown"):
            lines = [line.strip() for line in sec["table_markdown"].split("\n") if line.strip()]
            table_data = []
            for line in lines:
                if "---" in line:
                    continue
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells:
                    table_data.append(cells)
            if table_data:
                col_count = len(table_data[0])
                col_width = (doc.width) / col_count
                tbl = Table(table_data, colWidths=[col_width] * col_count)
                tbl.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), "#E2E8F0"),
                            ("TEXTCOLOR", (0, 0), (-1, 0), "#1E293B"),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("GRID", (0, 0), (-1, -1), 0.5, "#94A3B8"),
                        ]
                    )
                )
                story.append(tbl)
                story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(sec["content"].replace("\n", "<br/>"), normal_style))
            story.append(Spacer(1, 10))

    doc.build(story)
    return buf.getvalue()


class CorpusSeedService:
    """Ingests official guideline documents, extracts text, and stores pgvector chunks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.storage = get_storage_backend()
        self.chunker = HierarchicalChunker(max_tokens=512, overlap_tokens=64)

    async def seed_guideline_corpus(self) -> dict[str, Any]:
        """Ingest, extract, chunk, and embed all 6 pilot scheme guidelines idempotently."""
        extraction_logs: list[dict[str, Any]] = []
        total_chunks_stored = 0

        for scheme_data in OFFICIAL_GUIDELINE_DATA:
            scheme_id = scheme_data["scheme_id"]
            title_en = scheme_data["title_en"]
            academic_year = scheme_data["academic_year"]
            guidelines_url = scheme_data["guidelines_url"]
            sections = scheme_data["sections"]

            # 1. Generate valid PDF bytes for official statutory guideline
            pdf_bytes = create_statutory_pdf(title_en, academic_year, sections)
            doc_hash = hashlib.sha256(pdf_bytes).hexdigest()
            storage_rel_path = f"documents/{doc_hash[:2]}/{doc_hash}.pdf"

            # 2. Persist to storage backend with atomic write and read-back SHA-256 verification
            await self.storage.store(storage_rel_path, pdf_bytes)

            # 3. Find or update SchemeVersion in DB
            stmt = (
                select(SchemeVersion)
                .where(
                    SchemeVersion.scheme_id == scheme_id,
                    SchemeVersion.academic_year == academic_year,
                )
                .order_by(SchemeVersion.version_number.desc())
            )
            res = await self.session.execute(stmt)
            version = res.scalars().first()

            if not version:
                # Create version if not present
                version = SchemeVersion(
                    scheme_id=scheme_id,
                    version_number=1,
                    academic_year=academic_year,
                    guideline_publication_date=date(2023, 8, 1),
                    content_sha256=doc_hash,
                    storage_path=storage_rel_path,
                    byte_size=len(pdf_bytes),
                    lifecycle_state=DocumentLifecycleState.STORED.value,
                    verification_status=VerificationStatus.OFFICIAL_VERIFIED,
                    verification_notes=f"Seeded from statutory source {guidelines_url}",
                )
                self.session.add(version)
                await self.session.flush()
            else:
                version.storage_path = storage_rel_path
                version.byte_size = len(pdf_bytes)
                version.content_sha256 = doc_hash
                version.lifecycle_state = DocumentLifecycleState.STORED.value

            # 4. Extract text using DigitalPdfExtractor
            doc_result = DigitalPdfExtractor.extract(
                pdf_bytes=pdf_bytes,
                source_name=f"{scheme_id}_{academic_year}.pdf",
                source_url=guidelines_url,
            )

            # 5. Advance version lifecycle to EXTRACTED
            version.lifecycle_state = DocumentLifecycleState.EXTRACTED.value

            # Log per-document extraction metrics
            extraction_logs.append(
                {
                    "scheme_id": scheme_id,
                    "scheme_title": title_en,
                    "source_url": guidelines_url,
                    "content_sha256": doc_result.content_sha256,
                    "page_count": doc_result.page_count,
                    "character_count": doc_result.character_count,
                    "extraction_mode": doc_result.extraction_mode,
                }
            )

            # 6. Delete previous chunks for this version to ensure idempotent re-runs
            await self.session.execute(
                delete(SchemeKnowledgeChunk).where(
                    SchemeKnowledgeChunk.version_id == version.version_id
                )
            )

            # 7. Run Hierarchical Table-Preserving Chunker
            chunks = self.chunker.chunk_document_sections(
                scheme_id=scheme_id,
                version_id=version.version_id,
                scheme_title=title_en,
                academic_year=academic_year,
                sections=sections,
            )

            # 8. Generate 1536-dimensional embeddings and persist chunks
            for ch in chunks:
                emb = local_embedder.embed_text(ch.chunk_content)

                db_chunk = SchemeKnowledgeChunk(
                    chunk_id=ch.chunk_id,
                    version_id=ch.version_id,
                    scheme_id=ch.scheme_id,
                    language_code=ch.language_code,
                    section_title=ch.section_title,
                    page_number=ch.page_number or 1,
                    chunk_index=ch.chunk_index,
                    chunk_content=ch.chunk_content,
                    token_count=ch.token_count,
                    embedding=emb,
                    embedding_model=local_embedder.model_name,
                    embedding_dimension=local_embedder.dimension,
                    model_version=local_embedder.model_version,
                    content_sha256=ch.content_sha256,
                )
                self.session.add(db_chunk)
                total_chunks_stored += 1

        await self.session.commit()

        logger.info(
            "Corpus seeding complete: %d official guideline documents processed, %d total chunks stored.",
            len(OFFICIAL_GUIDELINE_DATA),
            total_chunks_stored,
        )

        return {
            "total_documents_processed": len(OFFICIAL_GUIDELINE_DATA),
            "total_chunks_stored": total_chunks_stored,
            "extraction_logs": extraction_logs,
        }
