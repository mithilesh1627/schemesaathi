"""Centralized Domain Exceptions and Error Handlers."""

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core.logging import get_logger, request_id_ctx
from src.core.security import sanitize_sensitive_data

logger = get_logger(__name__)


class StandardErrorEnvelope(BaseModel):
    """Standardized error envelope compliant with OpenAPI specification."""

    error_code: str = Field(..., examples=["ERR_ENTITY_NOT_FOUND"])
    message: str = Field(..., examples=["Resource not found."])
    details: dict[str, Any] | list[Any] | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    request_id: str | None = None


# Domain Exception Hierarchy
class SchemeSaathiError(Exception):
    """Base domain exception for SchemeSaathi."""

    def __init__(
        self,
        message: str,
        error_code: str = "ERR_INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundError(SchemeSaathiError):
    """Raised when an entity is not found in the database."""

    def __init__(self, entity_name: str, entity_id: str) -> None:
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' was not found.",
            error_code="ERR_ENTITY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity_name": entity_name, "entity_id": entity_id},
        )


class DuplicateDocumentError(SchemeSaathiError):
    """Raised when an identical document hash is already registered."""

    def __init__(self, sha256_hash: str, existing_id: str) -> None:
        super().__init__(
            message=f"Document with SHA-256 hash '{sha256_hash}' already exists in registry.",
            error_code="ERR_DUPLICATE_DOCUMENT",
            status_code=status.HTTP_409_CONFLICT,
            details={"sha256_hash": sha256_hash, "existing_id": existing_id},
        )


class InvalidStateError(SchemeSaathiError):
    """Raised when an operation is invalid for current entity state."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="ERR_INVALID_STATE",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class StatutoryRuleValidationError(SchemeSaathiError):
    """Raised when statutory rule definition fails validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="ERR_STATUTORY_RULE_INVALID",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details,
        )


class ServiceUnavailableError(SchemeSaathiError):
    """Raised when an external dependency (Database, Redis) is unavailable."""

    def __init__(self, service_name: str) -> None:
        super().__init__(
            message=f"Required service '{service_name}' is currently unavailable.",
            error_code="ERR_SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service_name": service_name},
        )


def build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """Build a standardized RFC-7807 compliant JSONResponse with PII scrubbing."""
    req_id = request_id_ctx.get()
    safe_message = str(sanitize_sensitive_data(message))
    safe_details = sanitize_sensitive_data(details) if details is not None else None
    envelope = StandardErrorEnvelope(
        error_code=error_code,
        message=safe_message,
        details=safe_details,
        request_id=req_id,
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized error handlers on the FastAPI application."""

    @app.exception_handler(SchemeSaathiError)
    async def handle_scheme_saathi_error(_request: Request, exc: SchemeSaathiError) -> JSONResponse:
        logger.warning(
            "Domain error occurred: %s [%s] status=%d",
            exc.message,
            exc.error_code,
            exc.status_code,
            extra={"details": exc.details},
        )
        return build_error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Request schema validation failed: %s", exc.errors())
        return build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="ERR_VALIDATION_FAILED",
            message="Request parameters or body failed schema validation.",
            details=exc.errors(),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        return build_error_response(
            status_code=exc.status_code,
            error_code=f"ERR_HTTP_{exc.status_code}",
            message=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", str(exc))
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ERR_INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
        )
