"""Pydantic models for async job status and result tracking."""

import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class JobResponse(BaseModel):
    job_id: str = Field(min_length=1, max_length=128, description="UUID job identifier")
    status: JobStatus
    result: Any | None = None
    error: str | None = None
    created_at: float | None = Field(default=None, description="Unix timestamp when job was created")

    @field_validator("job_id")
    @classmethod
    def _validate_job_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("job_id must not be blank")
        try:
            uuid.UUID(v)
        except (ValueError, AttributeError, TypeError) as e:
            raise ValueError(f"job_id must be a valid UUID, got {v!r}") from e
        return v

    @model_validator(mode="after")
    def _check_terminal_state(self):
        if self.status == JobStatus.DONE and self.result is None:
            raise ValueError("DONE jobs must include a result")
        if self.status == JobStatus.ERROR and not self.error:
            raise ValueError("ERROR jobs must include an error message")
        return self
