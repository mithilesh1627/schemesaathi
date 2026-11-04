"""Health, Liveness, Readiness, and Telemetry Endpoints."""

import time
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.database import check_database_health
from src.core.logging import get_logger
from src.core.redis import check_redis_health

logger = get_logger(__name__)

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health/live", summary="Liveness Probe", status_code=status.HTTP_200_OK)
async def liveness_probe() -> dict[str, str]:
    """Kubernetes / Container liveness probe. Returns 200 if process is running."""
    return {"status": "alive", "version": settings.VERSION}


@router.get("/health/ready", summary="Readiness Probe")
async def readiness_probe() -> JSONResponse:
    """Kubernetes / Container readiness probe.

    Verifies active connectivity to PostgreSQL and Redis.
    Returns 200 if ready to receive traffic, 503 if any core dependency fails.
    """
    db_ok = await check_database_health()
    redis_ok = await check_redis_health()

    is_ready = db_ok and redis_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    payload: dict[str, Any] = {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": {
            "database": "connected" if db_ok else "unreachable",
            "redis": "connected" if redis_ok else "unreachable",
        },
    }

    return JSONResponse(status_code=status_code, content=payload)


@router.get("/api/v1/telemetry/health", summary="Telemetry Health Status")
async def telemetry_health() -> JSONResponse:
    """Telemetry endpoint conforming to Milestone M0 OpenAPI contracts."""
    start_time = time.perf_counter()
    db_ok = await check_database_health()
    redis_ok = await check_redis_health()
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    is_healthy = db_ok and redis_ok
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    payload: dict[str, Any] = {
        "status": "HEALTHY" if is_healthy else "DEGRADED",
        "version": settings.VERSION,
        "database": "CONNECTED" if db_ok else "DISCONNECTED",
        "vector_extension": "PGVECTOR_ACTIVE" if db_ok else "UNKNOWN",
        "redis": "CONNECTED" if redis_ok else "DISCONNECTED",
        "latency_ms": duration_ms,
    }

    return JSONResponse(status_code=status_code, content=payload)
