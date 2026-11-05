"""Async Database Repositories for Scheme Catalog."""

from sqlalchemy import Text, and_, cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.domain.enums import PortalWindowStatus, SchemeLevel
from src.modules.catalog.domain.models import (
    Scheme,
    SchemeApplicationWindow,
    SchemeEligibilityRule,
    SchemeVersion,
)


class SchemeRepository:
    """Repository handling persistence operations for Schemes and Versions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, scheme_id: str, load_versions: bool = True) -> Scheme | None:
        """Fetch scheme by unique string ID with optional versions and nested components."""
        stmt = select(Scheme).where(Scheme.scheme_id == scheme_id)
        if load_versions:
            stmt = stmt.options(
                selectinload(Scheme.versions).selectinload(SchemeVersion.eligibility_rule),
                selectinload(Scheme.versions).selectinload(SchemeVersion.application_window),
                selectinload(Scheme.versions).selectinload(SchemeVersion.benefit),
                selectinload(Scheme.versions).selectinload(SchemeVersion.mandatory_documents),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_schemes(
        self,
        skip: int = 0,
        limit: int = 20,
        issuing_level: SchemeLevel | None = None,
        is_active: bool | None = True,
        category: str | None = None,
        domicile: str | None = None,
        course_level: str | None = None,
        portal_status: PortalWindowStatus | None = None,
    ) -> tuple[list[Scheme], int]:
        """Fetch paginated schemes with total count and statutory filters."""
        stmt = select(Scheme)
        count_stmt = select(func.count(func.distinct(Scheme.scheme_id))).select_from(Scheme)

        if is_active is not None:
            stmt = stmt.where(Scheme.is_active == is_active)
            count_stmt = count_stmt.where(Scheme.is_active == is_active)

        if issuing_level is not None:
            stmt = stmt.where(Scheme.issuing_level == issuing_level)
            count_stmt = count_stmt.where(Scheme.issuing_level == issuing_level)

        has_rule_filter = bool(category or domicile or course_level)
        needs_latest_version = has_rule_filter or (portal_status is not None)

        if needs_latest_version:
            # Subquery partitioning by scheme_id to resolve the single latest version
            latest_subq = select(
                SchemeVersion.version_id.label("latest_version_id"),
                SchemeVersion.scheme_id.label("sub_scheme_id"),
                func.row_number()
                .over(
                    partition_by=SchemeVersion.scheme_id,
                    order_by=SchemeVersion.version_number.desc(),
                )
                .label("rn"),
            ).subquery("latest_version_subq")

            stmt = stmt.join(
                latest_subq,
                and_(
                    latest_subq.c.sub_scheme_id == Scheme.scheme_id,
                    latest_subq.c.rn == 1,
                ),
            )
            count_stmt = count_stmt.join(
                latest_subq,
                and_(
                    latest_subq.c.sub_scheme_id == Scheme.scheme_id,
                    latest_subq.c.rn == 1,
                ),
            )

            if has_rule_filter:
                stmt = stmt.join(
                    SchemeEligibilityRule,
                    SchemeEligibilityRule.version_id == latest_subq.c.latest_version_id,
                )
                count_stmt = count_stmt.join(
                    SchemeEligibilityRule,
                    SchemeEligibilityRule.version_id == latest_subq.c.latest_version_id,
                )

                is_postgres = (
                    self.session.bind is not None and "postgresql" in self.session.bind.dialect.name
                )

                if category:
                    if is_postgres:
                        cat_clause = or_(
                            cast(SchemeEligibilityRule.target_categories, JSONB).contains(
                                [category]
                            ),
                            cast(SchemeEligibilityRule.target_categories, JSONB).contains(["ALL"]),
                        )
                    else:
                        cat_clause = or_(
                            cast(SchemeEligibilityRule.target_categories, Text).like(
                                f'%"{category}"%'
                            ),
                            cast(SchemeEligibilityRule.target_categories, Text).like('%"ALL"%'),
                        )
                    stmt = stmt.where(cat_clause)
                    count_stmt = count_stmt.where(cat_clause)

                if domicile:
                    if is_postgres:
                        dom_clause = or_(
                            cast(SchemeEligibilityRule.eligible_domiciles, JSONB).contains(
                                [domicile]
                            ),
                            cast(SchemeEligibilityRule.eligible_domiciles, JSONB).contains(
                                ["ALL_INDIA"]
                            ),
                        )
                    else:
                        dom_clause = or_(
                            cast(SchemeEligibilityRule.eligible_domiciles, Text).like(
                                f'%"{domicile}"%'
                            ),
                            cast(SchemeEligibilityRule.eligible_domiciles, Text).like(
                                '%"ALL_INDIA"%'
                            ),
                        )
                    stmt = stmt.where(dom_clause)
                    count_stmt = count_stmt.where(dom_clause)

                if course_level:
                    if is_postgres:
                        course_clause = or_(
                            cast(SchemeEligibilityRule.eligible_course_levels, JSONB).contains(
                                [course_level]
                            ),
                            cast(SchemeEligibilityRule.eligible_course_levels, JSONB).contains(
                                ["ALL"]
                            ),
                        )
                    else:
                        course_clause = or_(
                            cast(SchemeEligibilityRule.eligible_course_levels, Text).like(
                                f'%"{course_level}"%'
                            ),
                            cast(SchemeEligibilityRule.eligible_course_levels, Text).like(
                                '%"ALL"%'
                            ),
                        )
                    stmt = stmt.where(course_clause)
                    count_stmt = count_stmt.where(course_clause)

            if portal_status:
                stmt = stmt.join(
                    SchemeApplicationWindow,
                    SchemeApplicationWindow.version_id == latest_subq.c.latest_version_id,
                ).where(SchemeApplicationWindow.portal_status == portal_status)
                count_stmt = count_stmt.join(
                    SchemeApplicationWindow,
                    SchemeApplicationWindow.version_id == latest_subq.c.latest_version_id,
                ).where(SchemeApplicationWindow.portal_status == portal_status)

        stmt = stmt.options(
            selectinload(Scheme.versions).selectinload(SchemeVersion.eligibility_rule),
            selectinload(Scheme.versions).selectinload(SchemeVersion.application_window),
        )
        stmt = stmt.order_by(Scheme.title_en.asc()).offset(skip).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def create_scheme(self, scheme: Scheme) -> Scheme:
        """Persist a new scheme."""
        self.session.add(scheme)
        await self.session.flush()
        return scheme

    async def get_version_by_sha256(
        self, sha256_hash: str, scheme_id: str | None = None
    ) -> SchemeVersion | None:
        """Find an existing scheme version with identical SHA-256 hash, optionally scoped by scheme."""
        stmt = select(SchemeVersion).where(SchemeVersion.content_sha256 == sha256_hash)
        if scheme_id:
            stmt = stmt.where(SchemeVersion.scheme_id == scheme_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_next_version_number(self, scheme_id: str) -> int:
        """Get the next version number for a scheme."""
        stmt = select(func.coalesce(func.max(SchemeVersion.version_number), 0)).where(
            SchemeVersion.scheme_id == scheme_id
        )
        result = await self.session.execute(stmt)
        current_max: int = result.scalar_one()
        return current_max + 1

    async def create_version(self, version: SchemeVersion) -> SchemeVersion:
        """Persist a new scheme version."""
        self.session.add(version)
        await self.session.flush()
        return version
