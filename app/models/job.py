from enum import Enum
from typing import Any

from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: Any | None = None
    error: str | None = None
