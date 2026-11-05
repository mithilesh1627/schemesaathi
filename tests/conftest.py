"""Pytest Fixtures and Test Environment Setup."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import src.core.storage as storage_module
from src.core.config import settings
from src.core.database import get_db_session
from src.core.storage import LocalStorageBackend
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
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client configured with the test database session and admin credentials."""
    # Configure test admin key and isolated temporary storage directory
    test_admin_key = "test-admin-key-for-unit-tests-1234"
    monkeypatch.setattr(settings, "ADMIN_API_KEY", test_admin_key)
    monkeypatch.setattr(settings, "STORAGE_BASE_DIR", str(tmp_path))

    # Point default storage backend to temporary storage
    test_storage = LocalStorageBackend(base_dir=tmp_path)
    monkeypatch.setattr(storage_module, "_default_storage_backend", test_storage)

    # Ensure health checks report dependencies as healthy during API integration tests
    async def mock_redis_health() -> bool:
        return True

    async def mock_db_health() -> bool:
        return True

    monkeypatch.setattr("src.api.health.check_redis_health", mock_redis_health)
    monkeypatch.setattr("src.api.health.check_database_health", mock_db_health)

    # Mock Redis client for write rate limiting in tests
    mock_redis_counts: dict[str, int] = {}

    class TestMockRedis:
        async def incr(self, key: str) -> int:
            val = mock_redis_counts.get(key, 0) + 1
            mock_redis_counts[key] = val
            return val

        async def expire(self, _key: str, _seconds: int) -> bool:
            return True

        async def ttl(self, _key: str) -> int:
            return 60

        async def ping(self) -> bool:
            return True

        async def aclose(self) -> None:
            pass

    test_redis = TestMockRedis()
    monkeypatch.setattr("src.core.dependencies.get_redis_client", lambda: test_redis)

    app = create_app()

    # Override database dependency with test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    default_headers = {"X-Admin-API-Key": test_admin_key}
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=default_headers
    ) as client:
        yield client
