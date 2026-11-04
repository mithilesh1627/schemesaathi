"""Structured JSON and contextual logging for SchemeSaathi."""

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Context variable to propagate request_id across async calls
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter producing structured logs with request context."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).isoformat()
        req_id = request_id_ctx.get()

        log_data: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if req_id:
            log_data["request_id"] = req_id

        # Include extra fields if present
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: str = "INFO", format_type: str = "json") -> None:
    """Initialize root logging handler and formatter."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicate log records
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if format_type.lower() == "json":
        stream_handler.setFormatter(JSONFormatter())
    else:
        text_format = "%(asctime)s [%(levelname)s] [%(name)s] [req_id=%(request_id)s] %(message)s"
        stream_handler.setFormatter(logging.Formatter(text_format))

    root_logger.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    """Retrieve named logger."""
    return logging.getLogger(name)
