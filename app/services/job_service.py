import asyncio
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from app.core.log import get_logger
from app.models.job import JobResponse, JobStatus

logger = get_logger(__name__)


class Job:
    def __init__(self, job_id: str, name: str):
        self.job_id = job_id
        self.name = name
        self.status = JobStatus.PENDING
        self.result: Any = None
        self.error: str | None = None
        self.created_at = time.time()


class JobService:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._max_jobs = 100
        self._cleanup_interval = 300
        self._last_cleanup = time.time()

    def submit(self, name: str, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> JobResponse:
        job_id = str(uuid.uuid4())
        job = Job(job_id, name)
        self._jobs[job_id] = job

        async def _run():
            job.status = JobStatus.RUNNING
            try:
                job.result = await coro_factory()
                job.status = JobStatus.DONE
                logger.info("Job %s (%s) completed", job_id, name)
            except Exception as e:
                job.status = JobStatus.ERROR
                job.error = str(e)
                logger.exception("Job %s (%s) failed", job_id, name)

        asyncio.create_task(_run())
        self._maybe_cleanup()
        return JobResponse(job_id=job_id, status=job.status)

    def get_status(self, job_id: str) -> JobResponse | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return JobResponse(
            job_id=job.job_id,
            status=job.status,
            result=job.result,
            error=job.error,
        )

    def _maybe_cleanup(self):
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            cutoff = now - 3600
            self._jobs = {
                jid: j for jid, j in self._jobs.items()
                if j.status in (JobStatus.PENDING, JobStatus.RUNNING) or j.created_at > cutoff
            }
            if len(self._jobs) > self._max_jobs:
                pending = {jid: j for jid, j in self._jobs.items() if j.status in (JobStatus.PENDING, JobStatus.RUNNING)}
                completed = sorted(
                    [(jid, j) for jid, j in self._jobs.items() if j.status not in (JobStatus.PENDING, JobStatus.RUNNING)],
                    key=lambda x: x[1].created_at,
                    reverse=True,
                )
                keep = pending
                keep.update(dict(completed[:self._max_jobs // 2]))
                self._jobs = keep
            self._last_cleanup = now


_job_service: JobService | None = None


def get_job_service() -> JobService:
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service
