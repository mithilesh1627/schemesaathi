"""Async Database Engine Lifecycle and Session Management using SQLAlchemy 2."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Global engine and sessionmaker instances
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return or initialize the async database engine."""
    global _async_engine, _async_session_factory
    if _async_engine is None:
        # Check dialect
        is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

        engine_kwargs: dict[str, object] = {
            "echo": settings.DB_ECHO,
        }

        # Connection pool kwargs apply to non-SQLite
        if not is_sqlite:
            engine_kwargs.update(
                {
                    "pool_size": settings.DB_POOL_SIZE,
                    "max_overflow": settings.DB_MAX_OVERFLOW,
                    "pool_timeout": settings.DB_POOL_TIMEOUT,
                    "pool_recycle": settings.DB_POOL_RECYCLE,
                    "pool_pre_ping": True,
                    "connect_args": {
                        "server_settings": {
                            "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_MS),
                        }
                    },
                }
            )

        _async_engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.info(
            "Initialized async database engine for: %s", settings.DATABASE_URL.split("@")[-1]
        )

    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve session factory."""
    if _async_session_factory is None:
        get_engine()
    assert _async_session_factory is not None
    return _async_session_factory


async def close_db_engine() -> None:
    """Dispose of the database engine connection pool."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Async database engine disposed.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an isolated async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> bool:
    """Ping database using SELECT 1 to verify connectivity."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.error("Database health check failed: %s", str(exc))
        return False
