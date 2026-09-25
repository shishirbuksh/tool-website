"""Async job queue service: submit background tasks and poll results by ID."""

import asyncio
import threading
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from app.core.log import get_logger
from app.models.job import JobResponse, JobStatus

logger = get_logger(__name__)


class Job:
    def __init__(self, job_id: str, name: str) -> None:
        self.job_id = job_id
        self.name = name
        self.status = JobStatus.PENDING
        # Result may stay None even for DONE (degraded/empty upstream).
        self.result: Any | None = None
        self.error: str | None = None
        self.created_at = time.time()


class JobService:
    def __init__(self, max_concurrent: int = 10, task_timeout: float = 90.0) -> None:
        # task_timeout (90s) MUST stay < gunicorn timeout (see
        # gunicorn_conf.py TIMEOUT, default 320s). Gunicorn SIGKILLs workers
        # past TIMEOUT, so jobs must finish well before that.
        # NOTE: in-memory _jobs dict is per-process only; multi-worker
        # (gunicorn) deployments need a Redis shared store for cross-worker
        # job visibility.
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._tasks: set[asyncio.Task[Any]] = set()
        self._max_jobs = 100
        self._cleanup_interval = 300
        self._last_cleanup = time.time()
        self._max_concurrent = max_concurrent
        self._task_timeout = task_timeout
        # Async concurrency limiters per event loop (Uvicorn reload/tests create
        # new loops; a Semaphore bound to a closed loop raises RuntimeError).
        self._sems: dict[int, asyncio.Semaphore] = {}
        self._sem_lock = threading.Lock()

    def _get_sem(self) -> asyncio.Semaphore:
        loop_id = id(asyncio.get_running_loop())
        with self._sem_lock:
            sem = self._sems.get(loop_id)
            if sem is None:
                sem = asyncio.Semaphore(self._max_concurrent)
                self._sems[loop_id] = sem
                # Bound memory: drop stale loop entries.
                if len(self._sems) > 8:
                    oldest = next(iter(self._sems))
                    self._sems.pop(oldest, None)
            return sem

    def submit(self, name: str, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> JobResponse:
        if not callable(coro_factory):
            raise TypeError("coro_factory must be a callable returning a coroutine")
        job_id = str(uuid.uuid4())
        job = Job(job_id, name)
        with self._lock:
            self._jobs[job_id] = job

        async def _run():
            with self._lock:
                job.status = JobStatus.RUNNING
            try:
                sem = self._get_sem()
                try:
                    await asyncio.wait_for(sem.acquire(), timeout=10.0)
                except TimeoutError:
                    raise TimeoutError("Too many concurrent jobs (max 10)") from None
                try:
                    job.result = await asyncio.wait_for(coro_factory(), timeout=self._task_timeout)
                finally:
                    sem.release()
                with self._lock:
                    job.status = JobStatus.DONE
                logger.info("Job %s (%s) completed", job_id, name)
            except asyncio.CancelledError:
                with self._lock:
                    job.status = JobStatus.ERROR
                    job.error = "Job was cancelled"
                raise
            except Exception as e:
                with self._lock:
                    job.status = JobStatus.ERROR
                    # Keep str (not raw traceback object) but truncate to bound memory.
                    job.error = str(e)[:500]
                logger.exception("Job %s (%s) failed", job_id, name)

        try:
            task = asyncio.create_task(_run())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        except RuntimeError:
            raise RuntimeError("No running event loop available to schedule job") from None
        self._maybe_cleanup()
        return JobResponse(job_id=job_id, status=job.status, created_at=job.created_at)

    def get_status(self, job_id: str) -> JobResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return JobResponse(
                job_id=job.job_id,
                status=job.status,
                result=job.result,
                error=job.error,
                created_at=job.created_at,
            )

    def _maybe_cleanup(self) -> None:
        # NOTE: called inline on submit; for long-running servers hook this into
        # a background periodic task (e.g. lifespan loop every _cleanup_interval)
        # instead of relying solely on submit-triggered cleanup.
        # ROUND-2: interval-gated so idle servers don't leak finished jobs;
        # lifespan reaper in app/main.py calls cleanup_loop() periodically.
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            with self._lock:
                # Limit completed jobs memory footprint: max 5 minutes TTL
                cutoff = now - 300
                self._jobs = {
                    jid: j
                    for jid, j in self._jobs.items()
                    if j.status in (JobStatus.PENDING, JobStatus.RUNNING) or j.created_at > cutoff
                }
                if len(self._jobs) > self._max_jobs:
                    pending: dict[str, Job] = {}
                    completed: list[tuple[str, Job]] = []
                    for jid, j in self._jobs.items():
                        if j.status in (JobStatus.PENDING, JobStatus.RUNNING):
                            pending[jid] = j
                        else:
                            completed.append((jid, j))
                    # Keep at most 10 recent completed jobs to save RAM
                    completed.sort(key=lambda x: x[1].created_at, reverse=True)
                    pending.update(dict(completed[: 10]))
                    self._jobs = pending
            self._last_cleanup = now

    async def cleanup_loop(self, interval: float | None = None) -> None:
        """ROUND-2: lifespan reaper stub — run as background task from lifespan.

        Periodically calls _maybe_cleanup() every ``interval`` (defaults to
        self._cleanup_interval). Cancel on shutdown. Does not affect
        submit()/get_status() semantics.
        """
        import asyncio as _asyncio

        delay = interval if interval is not None else float(self._cleanup_interval)
        while True:
            try:
                await _asyncio.sleep(delay)
                self._maybe_cleanup()
            except _asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Job cleanup_loop iteration failed")



_job_service: JobService | None = None
_job_service_lock = threading.Lock()


def get_job_service() -> JobService:
    global _job_service
    if _job_service is None:
        with _job_service_lock:
            if _job_service is None:
                _job_service = JobService()
    return _job_service
