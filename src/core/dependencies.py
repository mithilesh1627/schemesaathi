"""FastAPI Dependencies for Administrative Authorization and Rate Limiting."""

import secrets

from fastapi import Request

from src.core.config import settings
from src.core.errors import (
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    ServiceUnavailableError,
)
from src.core.logging import get_logger
from src.core.redis import get_redis_client

logger = get_logger(__name__)


async def require_admin_key(request: Request) -> str:
    """Validate administrative API key from request headers.

    Accepts:
        - X-Admin-API-Key: <token>
        - Authorization: Bearer <token>

    Returns 401 if unauthenticated.
    Returns 403 if key is invalid.
    Fails closed (503) if ADMIN_API_KEY is unconfigured on server.
    Never logs or exposes the credential.
    """
    # 1. Check if ADMIN_API_KEY is configured on server
    configured_key = settings.ADMIN_API_KEY
    if not configured_key:
        logger.error(
            "ADMIN_API_KEY is not configured on the server. Rejecting write request (fail-closed)."
        )
        raise ServiceUnavailableError(
            "Administrative write operations are currently disabled: ADMIN_API_KEY is unconfigured on the server."
        )

    # 2. Extract credential from headers
    provided_key: str | None = request.headers.get("X-Admin-API-Key")
    if not provided_key:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            provided_key = auth_header[7:].strip()

    if not provided_key:
        raise AuthenticationError("Administrative credentials were not provided. Missing API key.")

    # 3. Constant-time comparison
    if not secrets.compare_digest(provided_key, configured_key):
        logger.warning("Rejected unauthorized administrative write attempt.")
        raise AuthorizationError("Invalid administrative API key.")

    return "admin"


async def enforce_write_rate_limit(request: Request) -> None:
    """Enforce Redis-backed rate limiting on administrative write operations.

    Returns 429 with Retry-After header if limit exceeded.
    Fails closed (503) if Redis is unreachable to prevent unthrottled writes.
    """
    # Extract client IP safely
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "unknown_client"

    key = f"rate_limit:write:{client_ip}"
    limit = settings.RATE_LIMIT_PER_MINUTE

    try:
        redis = get_redis_client()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)

        if count > limit:
            ttl = await redis.ttl(key)
            retry_after = max(ttl, 1)
            logger.warning(
                "Write rate limit exceeded for client %s: %d requests (limit: %d/min)",
                client_ip,
                count,
                limit,
            )
            raise RateLimitExceededError(retry_after=retry_after)
    except RateLimitExceededError:
        raise
    except Exception as exc:
        logger.error("Redis rate limit failure on write endpoint; failing closed: %s", exc)
        raise ServiceUnavailableError(
            "Rate limiting service is unavailable. Administrative write operations are temporarily disabled."
        ) from exc
