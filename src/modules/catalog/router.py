"""FastAPI Router for Scheme Catalog, Sources, and Document Ingestion."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.errors import EntityNotFoundError, InvalidStateError
from src.modules.catalog.application.ingestion_service import IngestionService
from src.modules.catalog.application.schemas import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    PaginatedSchemesResponse,
    SchemeCreate,
    SchemeDetailResponse,
    SchemeSummaryResponse,
    SchemeVersionResponse,
    SourceRegistryResponse,
)
from src.modules.catalog.application.source_registry_service import SourceRegistryService
from src.modules.catalog.domain.enums import PortalWindowStatus, SchemeLevel
from src.modules.catalog.domain.models import Scheme
from src.modules.catalog.infrastructure.repositories import SchemeRepository

router = APIRouter(tags=["Catalog & Ingestion"])


@router.get(
    "/schemes/catalog",
    response_model=PaginatedSchemesResponse,
    summary="Retrieve Paginated Scheme Catalog",
)
async def get_schemes_catalog(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    issuing_level: SchemeLevel | None = Query(
        default=None, description="Filter by statutory level"
    ),
    is_active: bool | None = Query(default=True, description="Filter active status"),
    category: str | None = Query(
        default=None, description="Filter by social category (e.g. ST, SC, OBC, GENERAL)"
    ),
    domicile: str | None = Query(
        default=None, description="Filter by state domicile (e.g. MANIPUR)"
    ),
    course_level: str | None = Query(
        default=None, description="Filter by course level (e.g. UNDERGRADUATE, POSTGRADUATE)"
    ),
    portal_status: PortalWindowStatus | None = Query(
        default=None, description="Filter by application portal window status"
    ),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedSchemesResponse:
    """Retrieve catalog of schemes with optional filtering and pagination."""
    skip = (page - 1) * limit
    repo = SchemeRepository(db)
    schemes, total = await repo.list_schemes(
        skip=skip,
        limit=limit,
        issuing_level=issuing_level,
        is_active=is_active,
        category=category,
        domicile=domicile,
        course_level=course_level,
        portal_status=portal_status,
    )

    items: list[SchemeSummaryResponse] = []
    for s in schemes:
        latest_ver = max(s.versions, key=lambda v: v.version_number) if s.versions else None
        p_status = (
            latest_ver.application_window.portal_status
            if (latest_ver and latest_ver.application_window)
            else None
        )
        inc_ceiling = (
            float(latest_ver.eligibility_rule.income_ceiling_annual_inr)
            if (
                latest_ver
                and latest_ver.eligibility_rule
                and latest_ver.eligibility_rule.income_ceiling_annual_inr is not None
            )
            else None
        )
        items.append(
            SchemeSummaryResponse(
                scheme_id=s.scheme_id,
                official_code=s.official_code,
                title_en=s.title_en,
                title_mni_beng=s.title_mni_beng,
                issuing_level=s.issuing_level,
                ministry_or_department=s.ministry_or_department,
                is_active=s.is_active,
                latest_academic_year=latest_ver.academic_year if latest_ver else None,
                portal_status=p_status,
                income_ceiling_annual_inr=inc_ceiling,
            )
        )

    return PaginatedSchemesResponse(
        total=total,
        page=page,
        limit=limit,
        items=items,
    )


@router.get(
    "/schemes/{scheme_id}",
    response_model=SchemeDetailResponse,
    summary="Get Detailed Scheme Definition",
)
async def get_scheme_by_id(
    scheme_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> SchemeDetailResponse:
    """Fetch complete scheme details including versions and guidelines."""
    repo = SchemeRepository(db)
    scheme = await repo.get_by_id(scheme_id)
    if not scheme:
        raise EntityNotFoundError(entity_name="Scheme", entity_id=scheme_id)

    versions = [
        SchemeVersionResponse.model_validate(v)
        for v in sorted(scheme.versions, key=lambda x: x.version_number, reverse=True)
    ]

    return SchemeDetailResponse(
        scheme_id=scheme.scheme_id,
        official_code=scheme.official_code,
        title_en=scheme.title_en,
        title_hi=scheme.title_hi,
        title_mni_beng=scheme.title_mni_beng,
        title_mni_latn=scheme.title_mni_latn,
        issuing_level=scheme.issuing_level,
        ministry_or_department=scheme.ministry_or_department,
        implementing_agency=scheme.implementing_agency,
        canonical_source_url=scheme.canonical_source_url,
        guidelines_document_url=scheme.guidelines_document_url,
        is_active=scheme.is_active,
        created_at=scheme.created_at,
        updated_at=scheme.updated_at,
        versions=versions,
    )


@router.post(
    "/schemes/",
    response_model=SchemeDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a New Scheme",
)
async def create_scheme(
    payload: SchemeCreate,
    db: AsyncSession = Depends(get_db_session),
) -> SchemeDetailResponse:
    """Create a new scholarship scheme in the catalog."""
    repo = SchemeRepository(db)
    existing = await repo.get_by_id(payload.scheme_id, load_versions=False)
    if existing:
        raise InvalidStateError(
            message=f"Scheme with ID '{payload.scheme_id}' already exists.",
            details={"scheme_id": payload.scheme_id},
        )

    new_scheme = Scheme(
        scheme_id=payload.scheme_id,
        official_code=payload.official_code,
        title_en=payload.title_en,
        title_hi=payload.title_hi,
        title_mni_beng=payload.title_mni_beng,
        title_mni_latn=payload.title_mni_latn,
        issuing_level=payload.issuing_level,
        ministry_or_department=payload.ministry_or_department,
        implementing_agency=payload.implementing_agency,
        canonical_source_url=payload.canonical_source_url,
        guidelines_document_url=payload.guidelines_document_url,
        is_active=payload.is_active,
    )

    await repo.create_scheme(new_scheme)
    await db.commit()
    await db.refresh(new_scheme)

    return SchemeDetailResponse(
        scheme_id=new_scheme.scheme_id,
        official_code=new_scheme.official_code,
        title_en=new_scheme.title_en,
        title_hi=new_scheme.title_hi,
        title_mni_beng=new_scheme.title_mni_beng,
        title_mni_latn=new_scheme.title_mni_latn,
        issuing_level=new_scheme.issuing_level,
        ministry_or_department=new_scheme.ministry_or_department,
        implementing_agency=new_scheme.implementing_agency,
        canonical_source_url=new_scheme.canonical_source_url,
        guidelines_document_url=new_scheme.guidelines_document_url,
        is_active=new_scheme.is_active,
        created_at=new_scheme.created_at,
        updated_at=new_scheme.updated_at,
        versions=[],
    )


@router.get(
    "/sources/registry",
    response_model=SourceRegistryResponse,
    summary="List Official Government Portals & Sources",
)
async def get_source_registry() -> SourceRegistryResponse:
    """Retrieve immutable registry of verified official government portals (M0 Baseline)."""
    return SourceRegistryService.get_all_sources()


@router.post(
    "/ingest/document",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Official Document with SHA-256 Deduplication",
)
async def ingest_document(
    payload: DocumentIngestRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DocumentIngestResponse:
    """Ingest a policy PDF or circular with cryptographic SHA-256 deduplication."""
    service = IngestionService(db)
    return await service.ingest_document(payload)
