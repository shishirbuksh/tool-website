"""JSON logging with contextvars-based request ID propagation."""

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


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
        rid = _request_id_var.get()
        if rid:
            msg["request_id"] = rid
        return json.dumps(msg, default=str)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(request_id: str) -> contextvars.Token:
    return _request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    _request_id_var.reset(token)
