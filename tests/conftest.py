"""Pytest Fixtures and Test Environment Setup."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.database import get_db_session
from src.main import create_app
from src.modules.catalog.domain.models import Base

# Test database: isolated in-memory SQLite with async connection
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async SQLite engine for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    # Initialize all database tables on the test engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session rolled back after each test."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client configured with the test database session."""

    # Ensure health checks report dependencies as healthy during API integration tests
    async def mock_redis_health() -> bool:
        return True

    async def mock_db_health() -> bool:
        return True

    monkeypatch.setattr("src.api.health.check_redis_health", mock_redis_health)
    monkeypatch.setattr("src.api.health.check_database_health", mock_db_health)

    app = create_app()

    # Override database dependency with test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
