"""Middleware Components: Request ID Propagation and Access Timing."""

import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger, request_id_ctx
from src.core.security import redact_aadhaar_pii

logger = get_logger("schemesaathi.access")

# Strict alphanumeric, hyphen, underscore format to prevent header injection / CRLF
_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{8,64}$")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generates or validates X-Request-ID and tracks request execution latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        # Validate format to prevent CRLF injection, control characters, or oversized headers
        if incoming_id and _REQUEST_ID_PATTERN.match(incoming_id):
            req_id = incoming_id
        else:
            req_id = str(uuid.uuid4())

        # Set context variable for duration of request
        token = request_id_ctx.set(req_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Attach request id and execution duration headers
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time-MS"] = f"{duration_ms:.2f}"

            # Scrub URL path of any prospective PII before logging access
            safe_path = redact_aadhaar_pii(request.url.path)

            # Access log
            logger.info(
                "%s %s -> status=%d duration=%.2fms",
                request.method,
                safe_path,
                response.status_code,
                duration_ms,
            )
            return response
        finally:
            request_id_ctx.reset(token)
