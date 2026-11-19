"""Async job models and status enumerations."""

from __future__ import annotations

import uuid
from enum import StrEnum
from dataclasses import dataclass
from typing import Any


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class JobResponse:
    job_id: str
    status: JobStatus
    result: Any | None = None
    error: str | None = None
    created_at: float | None = None

    def __post_init__(self):
        v = self.job_id.strip() if self.job_id else ""
        if not v:
            raise ValueError("job_id must not be blank")
        try:
            uuid.UUID(v)
        except (ValueError, AttributeError, TypeError) as e:
            raise ValueError(f"job_id must be a valid UUID, got {v!r}") from e
        if self.status == JobStatus.ERROR and not self.error:
            raise ValueError("ERROR jobs must include an error message")
