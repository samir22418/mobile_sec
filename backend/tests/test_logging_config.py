"""Tests for the structured JSON logging configuration."""
from __future__ import annotations

import json
import logging


from app.logging_config import _JsonFormatter, configure_logging


def test_json_formatter_produces_valid_json():
    record = logging.LogRecord(
        name="aegis.test", level=logging.INFO, pathname="", lineno=0,
        msg="hello %s", args=("world",), exc_info=None,
    )
    formatter = _JsonFormatter()
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["msg"] == "hello world"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "aegis.test"
    assert "ts" in parsed


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="aegis.test", level=logging.ERROR, pathname="", lineno=0,
        msg="oops", args=(), exc_info=exc_info,
    )
    formatter = _JsonFormatter()
    parsed = json.loads(formatter.format(record))
    assert "boom" in parsed["exc"]


def test_json_formatter_extra_fields_included():
    record = logging.LogRecord(
        name="aegis.test", level=logging.WARNING, pathname="", lineno=0,
        msg="check extra", args=(), exc_info=None,
    )
    record.payload_id = "p-123"
    formatter = _JsonFormatter()
    parsed = json.loads(formatter.format(record))
    assert parsed["payload_id"] == "p-123"


def test_configure_logging_is_idempotent():
    """Calling configure_logging twice should not add duplicate handlers."""
    # Already called by create_app in conftest; calling again must not error
    root = logging.getLogger()
    before = len(root.handlers)
    configure_logging()
    after = len(root.handlers)
    assert after == before  # no duplicate added
