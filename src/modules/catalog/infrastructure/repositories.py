"""Async Database Repositories for Scheme Catalog."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.domain.enums import SchemeLevel
from src.modules.catalog.domain.models import Scheme, SchemeVersion


class SchemeRepository:
    """Repository handling persistence operations for Schemes and Versions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, scheme_id: str, load_versions: bool = True) -> Scheme | None:
        """Fetch scheme by unique string ID with optional versions."""
        stmt = select(Scheme).where(Scheme.scheme_id == scheme_id)
        if load_versions:
            stmt = stmt.options(selectinload(Scheme.versions))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_schemes(
        self,
        skip: int = 0,
        limit: int = 20,
        issuing_level: SchemeLevel | None = None,
        is_active: bool | None = True,
    ) -> tuple[list[Scheme], int]:
        """Fetch paginated schemes with total count."""
        stmt = select(Scheme)
        count_stmt = select(func.count()).select_from(Scheme)

        if is_active is not None:
            stmt = stmt.where(Scheme.is_active == is_active)
            count_stmt = count_stmt.where(Scheme.is_active == is_active)

        if issuing_level is not None:
            stmt = stmt.where(Scheme.issuing_level == issuing_level)
            count_stmt = count_stmt.where(Scheme.issuing_level == issuing_level)

        stmt = stmt.options(selectinload(Scheme.versions))
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

    async def get_version_by_sha256(self, sha256_hash: str) -> SchemeVersion | None:
        """Find an existing scheme version with identical SHA-256 hash."""
        stmt = select(SchemeVersion).where(SchemeVersion.content_sha256 == sha256_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
