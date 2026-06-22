import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if isinstance(record.exc_info, (list, tuple)) and record.exc_info[0]:
            msg["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            msg["request_id"] = record.request_id
        return json.dumps(msg, default=str)


class RequestIDFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self._request_id = ""

    def set_request_id(self, request_id: str):
        self._request_id = request_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self._request_id
        return True


_request_id_filter = RequestIDFilter()


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(_request_id_filter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def get_request_id_filter() -> RequestIDFilter:
    return _request_id_filter
