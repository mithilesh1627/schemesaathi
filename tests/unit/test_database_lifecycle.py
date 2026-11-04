"""Unit Tests for Database Engine Lifecycle, Sessions, and Health Checking."""

import pytest
from sqlalchemy import text

from src.core.config import settings
from src.core.database import (
    check_database_health,
    close_db_engine,
    get_db_session,
    get_engine,
    get_session_factory,
)


@pytest.mark.asyncio
async def test_database_lifecycle_and_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify engine initialization, session factory creation, session dependency, and disposal."""
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    # Ensure clean state
    await close_db_engine()

    # 1. Initialize engine
    engine = get_engine()
    assert engine is not None

    # Calling again returns cached instance
    engine2 = get_engine()
    assert engine is engine2

    # 2. Retrieve session factory
    factory = get_session_factory()
    assert factory is not None

    # 3. Test database health check ping
    is_healthy = await check_database_health()
    assert is_healthy is True

    # 4. Test get_db_session dependency generator
    session_gen = get_db_session()
    session = await anext(session_gen)
    assert session is not None
    res = await session.execute(text("SELECT 42"))
    assert res.scalar() == 42
    with pytest.raises(StopAsyncIteration):
        await anext(session_gen)

    # 5. Test get_db_session error handling / rollback branch
    session_gen2 = get_db_session()
    _ = await anext(session_gen2)
    with pytest.raises(RuntimeError, match="Simulated session error"):
        await session_gen2.athrow(RuntimeError("Simulated session error"))

    # 6. Dispose engine
    await close_db_engine()
    # Calling close again is idempotent
    await close_db_engine()


@pytest.mark.asyncio
async def test_database_health_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify check_database_health returns False when database connection raises exception."""
    # Point to invalid connection URI to force failure
    monkeypatch.setattr(
        settings, "DATABASE_URL", "sqlite+aiosqlite:///invalid/path/that/cannot/exist/db.sqlite"
    )
    await close_db_engine()

    is_healthy = await check_database_health()
    assert is_healthy is False

    await close_db_engine()
