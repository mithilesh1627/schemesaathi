"""Main FastAPI Application Entry Point for SchemeSaathi Modular Monolith."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from src.api.health import router as health_router
from src.core.config import settings
from src.core.database import close_db_engine, get_engine, get_session_factory
from src.core.errors import register_exception_handlers
from src.core.logging import get_logger, setup_logging
from src.core.middleware import RequestIDMiddleware, RequestSizeLimitMiddleware
from src.core.redis import close_redis
from src.modules.catalog.infrastructure.seed_data import seed_pilot_schemes
from src.modules.catalog.router import router as catalog_router
from src.modules.chat.router import router as chat_router
from src.modules.eligibility.router import router as eligibility_router
from src.modules.retrieval.application.corpus_seed_service import CorpusSeedService
from src.modules.retrieval.router import router as retrieval_router

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
        if not settings.is_production:
            try:
                session_factory = get_session_factory()
                async with session_factory() as session:
                    await seed_pilot_schemes(session)
                    seed_service = CorpusSeedService(session)
                    await seed_service.seed_guideline_corpus()
            except Exception as seed_err:
                logger.warning("Auto-seed on startup skipped: %s", seed_err)
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
            "Milestone M1 Sprint 1 & Sprint 2 Backend Modular Monolith."
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
    app.include_router(eligibility_router, prefix=settings.API_V1_PREFIX)
    app.include_router(retrieval_router, prefix=settings.API_V1_PREFIX)
    app.include_router(chat_router, prefix=settings.API_V1_PREFIX)

    # 5. Mount Static Assets
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 6. Register PWA Shell Routes
    @app.get(
        "/",
        response_class=HTMLResponse,
        tags=["PWA"],
        summary="SchemeSaathi PWA Shell",
    )
    @app.get(
        "/app",
        response_class=HTMLResponse,
        tags=["PWA"],
        summary="SchemeSaathi PWA Application View",
    )
    async def get_pwa_shell() -> HTMLResponse:
        """Serve installable offline-capable PWA client."""
        template_path = Path(__file__).parent / "templates" / "pwa.html"
        if template_path.is_file():
            return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>PWA template not found</h1>", status_code=404)

    @app.get("/manifest.json", tags=["PWA"], summary="PWA Web App Manifest")
    async def get_manifest() -> Response:
        """Serve PWA manifest with standard manifest MIME type."""
        manifest_path = Path(__file__).parent / "static" / "manifest.json"
        if manifest_path.is_file():
            return Response(
                content=manifest_path.read_text(encoding="utf-8"),
                media_type="application/manifest+json",
            )
        return Response(content="{}", media_type="application/manifest+json", status_code=404)

    @app.get("/sw.js", tags=["PWA"], summary="PWA Service Worker")
    async def get_service_worker() -> Response:
        """Serve service worker with root scope permissions."""
        sw_path = Path(__file__).parent / "static" / "sw.js"
        if sw_path.is_file():
            return Response(
                content=sw_path.read_text(encoding="utf-8"),
                media_type="application/javascript",
                headers={"Service-Worker-Allowed": "/"},
            )
        return Response(
            content="// sw not found", media_type="application/javascript", status_code=404
        )

    # 7. Register Thin Demo Webpage
    @app.get(
        "/demo",
        response_class=HTMLResponse,
        tags=["Demo"],
        summary="Manipur Pilot Interactive Demo",
    )
    async def get_demo_page() -> HTMLResponse:
        """Serve minimal single-page demo for reviewer evaluation."""
        template_path = Path(__file__).parent / "templates" / "demo.html"
        if template_path.is_file():
            return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Demo template not found</h1>", status_code=404)

    # 8. Register Thin Chat Demo Webpage
    @app.get(
        "/chat",
        response_class=HTMLResponse,
        tags=["Demo"],
        summary="Manipur Pilot Grounded Chat Demo",
    )
    async def get_chat_page() -> HTMLResponse:
        """Serve minimal single-page grounded chat demo for reviewer evaluation."""
        template_path = Path(__file__).parent / "templates" / "chat.html"
        if template_path.is_file():
            return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Chat demo template not found</h1>", status_code=404)

    return app


app = create_app()
