"""Unit Tests for Structured JSON and Contextual Logging."""

import json
import logging
import sys

from src.core.logging import JSONFormatter, get_logger, request_id_ctx, setup_logging


def test_json_formatter_standard_record() -> None:
    """Verify JSONFormatter encodes basic record into valid JSON."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="schemesaathi.catalog",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Scheme %s loaded successfully",
        args=("sch-mn-001",),
        exc_info=None,
    )

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["logger"] == "schemesaathi.catalog"
    assert data["message"] == "Scheme sch-mn-001 loaded successfully"
    assert "timestamp" in data
    assert "request_id" not in data


def test_json_formatter_with_request_id_and_extra_and_exception() -> None:
    """Verify request context, extra metadata dictionary, and exception formatting."""
    formatter = JSONFormatter()

    token = request_id_ctx.set("req-test-uuid-1234")
    try:
        try:
            raise ValueError("Test internal error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="schemesaathi.error",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="Failure processing rule",
            args=(),
            exc_info=exc_info,
        )
        record.__dict__["extra"] = {"rule_id": "rule-42", "scheme_id": "sch-001"}

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "ERROR"
        assert data["request_id"] == "req-test-uuid-1234"
        assert data["rule_id"] == "rule-42"
        assert data["scheme_id"] == "sch-001"
        assert "exception" in data
        assert "ValueError: Test internal error" in data["exception"]
    finally:
        request_id_ctx.reset(token)


def test_setup_logging_json_and_text() -> None:
    """Verify setup_logging configures root logger in JSON and text modes."""
    # Test JSON mode
    setup_logging(level="DEBUG", format_type="json")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JSONFormatter)

    # Test text mode
    setup_logging(level="WARNING", format_type="text")
    assert root.level == logging.WARNING
    assert len(root.handlers) == 1
    assert not isinstance(root.handlers[0].formatter, JSONFormatter)

    # Reset back to default
    setup_logging(level="INFO", format_type="json")


def test_get_logger() -> None:
    """Verify get_logger returns logger instance with specified name."""
    logger = get_logger("my_test_module")
    assert logger.name == "my_test_module"
