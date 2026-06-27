import json
import logging

from app.core.log import JSONFormatter, RequestIDFilter


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
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=5,
            msg="warn msg",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-123"
        output = json.loads(formatter.format(record))
        assert output["request_id"] == "req-123"
        assert output["message"] == "warn msg"

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


class TestRequestIDFilter:
    def test_filter_sets_request_id(self):
        filt = RequestIDFilter()
        filt.set_request_id("abc-123")
        record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        assert filt.filter(record)
        assert record.request_id == "abc-123"

    def test_default_request_id_empty(self):
        filt = RequestIDFilter()
        record = logging.LogRecord("t", logging.INFO, "", 0, "msg", (), None)
        filt.filter(record)
        assert record.request_id == ""
