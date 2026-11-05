"""Main FastAPI Application Entry Point for SchemeSaathi Modular Monolith."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.health import router as health_router
from src.core.config import settings
from src.core.database import close_db_engine, get_engine
from src.core.errors import register_exception_handlers
from src.core.logging import get_logger, setup_logging
from src.core.middleware import RequestIDMiddleware, RequestSizeLimitMiddleware
from src.core.redis import close_redis
from src.modules.catalog.router import router as catalog_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and graceful shutdown."""
    # 1. Startup phase
    setup_logging(level=settings.LOG_LEVEL, format_type=settings.LOG_FORMAT)
    logger.info(
        "Starting %s v%s [Environment: %s]",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )

    # Initialize DB connection pool eagerly
    try:
        get_engine()
    except Exception as exc:
        logger.error("Database connection initialization warning: %s", str(exc))

    yield

    # 2. Shutdown phase
    logger.info("Initiating graceful shutdown...")
    await close_redis()
    await close_db_engine()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="SchemeSaathi API",
        description=(
            "Intelligent Multilingual Indian Government Scholarship Discovery Platform. "
            "Milestone M1 Sprint 1 Backend Modular Monolith."
        ),
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # 1. Register Core Middleware (Request ID, Size Limiter, CORS)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Centralized Error Handlers
    register_exception_handlers(app)

    # 3. Register Health & Telemetry Routes
    app.include_router(health_router)

    # 4. Register Bounded Context Routers
    app.include_router(catalog_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
