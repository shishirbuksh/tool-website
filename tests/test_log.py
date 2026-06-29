"""Tests for JSONFormatter and contextvars-based request ID propagation."""

import json
import logging

from app.core.log import JSONFormatter, reset_request_id, set_request_id


class TestJSONFormatter:
    def test_format_basic(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = json.loads(formatter.format(record))
        assert output["message"] == "hello world"
        assert output["level"] == "INFO"
        assert output["logger"] == "test_logger"
        assert "timestamp" in output

    def test_format_with_request_id(self):
        formatter = JSONFormatter()
        token = set_request_id("req-123")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.WARNING,
                pathname=__file__,
                lineno=5,
                msg="warn msg",
                args=(),
                exc_info=None,
            )
            output = json.loads(formatter.format(record))
            assert output["request_id"] == "req-123"
            assert output["message"] == "warn msg"
        finally:
            reset_request_id(token)

    def test_format_without_request_id(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=5,
            msg="no-rid msg",
            args=(),
            exc_info=None,
        )
        output = json.loads(formatter.format(record))
        assert "request_id" not in output
        assert output["message"] == "no-rid msg"

    def test_format_with_exception(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=20,
                msg="error occurred",
                args=(),
                exc_info=exc_info,
            )
        output = json.loads(formatter.format(record))
        assert "exception" in output
        assert "ValueError" in output["exception"]
        assert "test error" in output["exception"]


class TestRequestIDContext:
    def test_set_and_reset(self):
        token = set_request_id("abc-123")
        try:
            formatter = JSONFormatter()
            record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
            output = json.loads(formatter.format(record))
            assert output["request_id"] == "abc-123"
        finally:
            reset_request_id(token)

        record2 = logging.LogRecord("t", logging.INFO, "", 0, "msg2", (), None)
        output2 = json.loads(formatter.format(record2))
        assert "request_id" not in output2

    def test_default_empty(self):
        formatter = JSONFormatter()
        record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        output = json.loads(formatter.format(record))
        assert "request_id" not in output
