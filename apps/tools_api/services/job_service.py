"""Async job queue service: submit background tasks and poll results by ID."""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from apps.core.log import get_logger
from apps.tools_api.models import JobResponse, JobStatus

logger = get_logger(__name__)


class Job:
    def __init__(self, job_id: str, name: str) -> None:
        self.job_id = job_id
        self.name = name
        self.status = JobStatus.PENDING
        self.result: Any | None = None
        self.error: str | None = None
        self.created_at = time.time()


class JobService:
    def __init__(self, max_concurrent: int = 10, task_timeout: float = 90.0) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._tasks: set[asyncio.Task[Any]] = set()
        self._max_jobs = 100
        self._cleanup_interval = 300
        self._last_cleanup = time.time()
        self._max_concurrent = max_concurrent
        self._task_timeout = task_timeout
        self._sems: dict[int, asyncio.Semaphore] = {}
        self._sem_lock = threading.Lock()

    def _get_sem(self) -> asyncio.Semaphore:
        loop_id = id(asyncio.get_running_loop())
        with self._sem_lock:
            sem = self._sems.get(loop_id)
            if sem is None:
                sem = asyncio.Semaphore(self._max_concurrent)
                self._sems[loop_id] = sem
                if len(self._sems) > 8:
                    oldest = next(iter(self._sems))
                    self._sems.pop(oldest, None)
            return sem

    def _sync_cache(self, job: Job) -> None:
        try:
            from apps.core.cache import get_cache

            data = {
                "job_id": job.job_id,
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                "result": job.result,
                "error": job.error,
                "created_at": job.created_at,
            }
            get_cache().set(f"job:{job.job_id}", data, ttl=600)
        except Exception:
            pass

    def submit(self, name: str, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> JobResponse:
        if not callable(coro_factory):
            raise TypeError("coro_factory must be a callable returning a coroutine")
        job_id = str(uuid.uuid4())
        job = Job(job_id, name)
        with self._lock:
            active = sum(1 for j in self._jobs.values() if j.status in (JobStatus.PENDING, JobStatus.RUNNING))
            if active >= self._max_jobs:
                msg = f"Job queue full ({active} active jobs, max {self._max_jobs})"
                raise RuntimeError(msg)
            self._jobs[job_id] = job
        self._sync_cache(job)

        async def _run():
            with self._lock:
                job.status = JobStatus.RUNNING
            self._sync_cache(job)
            try:
                sem = self._get_sem()
                try:
                    await asyncio.wait_for(sem.acquire(), timeout=3600.0)
                except TimeoutError:
                    raise TimeoutError("Too many concurrent jobs (max 10)") from None
                try:
                    job.result = await asyncio.wait_for(coro_factory(), timeout=self._task_timeout)
                finally:
                    sem.release()
                with self._lock:
                    job.status = JobStatus.DONE
                self._sync_cache(job)
                logger.info("Job %s (%s) completed", job_id, name)
            except asyncio.CancelledError:
                with self._lock:
                    job.status = JobStatus.ERROR
                    job.error = "Job was cancelled"
                self._sync_cache(job)
                raise
            except Exception as e:
                with self._lock:
                    job.status = JobStatus.ERROR
                    job.error = str(e)[:500]
                self._sync_cache(job)
                logger.exception("Job %s (%s) failed", job_id, name)

        try:
            task = asyncio.create_task(_run())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        except RuntimeError:
            raise RuntimeError("No running event loop available to schedule job") from None
        self._maybe_cleanup()
        return JobResponse(job_id=job_id, status=job.status, created_at=job.created_at)

    def submit_background(self, name: str, coro_factory: Callable[[], Coroutine[Any, Any, Any]]) -> JobResponse:
        """Schedule coroutine job in either running event loop (ASGI) or daemon thread loop (WSGI)."""
        try:
            asyncio.get_running_loop()
            return self.submit(name, coro_factory)
        except RuntimeError:
            pass

        if not callable(coro_factory):
            raise TypeError("coro_factory must be a callable returning a coroutine")
        job_id = str(uuid.uuid4())
        job = Job(job_id, name)
        with self._lock:
            active = sum(1 for j in self._jobs.values() if j.status in (JobStatus.PENDING, JobStatus.RUNNING))
            if active >= self._max_jobs:
                raise RuntimeError(f"Job queue full ({active} active jobs, max {self._max_jobs})")
            self._jobs[job_id] = job
        self._sync_cache(job)

        def _thread_runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                with self._lock:
                    job.status = JobStatus.RUNNING
                self._sync_cache(job)
                job.result = loop.run_until_complete(asyncio.wait_for(coro_factory(), timeout=self._task_timeout))
                with self._lock:
                    job.status = JobStatus.DONE
                self._sync_cache(job)
            except Exception as e:
                with self._lock:
                    job.status = JobStatus.ERROR
                    job.error = str(e)[:500] or "Job failed"
                self._sync_cache(job)
                logger.exception("Background job %s (%s) failed", job_id, name)
            finally:
                loop.close()

        t = threading.Thread(target=_thread_runner, daemon=True, name=f"job-{job_id[:8]}")
        t.start()
        self._maybe_cleanup()
        return JobResponse(job_id=job_id, status=job.status, created_at=job.created_at)

    def get_status(self, job_id: str) -> JobResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return JobResponse(
                    job_id=job.job_id,
                    status=job.status,
                    result=job.result,
                    error=job.error,
                    created_at=job.created_at,
                )
        try:
            from apps.core.cache import get_cache

            cached = get_cache().get(f"job:{job_id}")
            if isinstance(cached, dict):
                raw_st = str(cached.get("status", JobStatus.PENDING.value))
                st = JobStatus(raw_st) if raw_st in JobStatus._value2member_map_ else JobStatus.PENDING
                err = cached.get("error")
                if st == JobStatus.ERROR and not err:
                    err = "Unknown error"
                return JobResponse(
                    job_id=str(cached.get("job_id", job_id)),
                    status=st,
                    result=cached.get("result"),
                    error=err,
                    created_at=float(cached.get("created_at", time.time())),
                )
        except Exception:
            pass
        return None

    def _maybe_cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            with self._lock:
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
                    completed.sort(key=lambda x: x[1].created_at, reverse=True)
                    pending.update(dict(completed[:10]))
                    self._jobs = pending
            self._last_cleanup = now


_job_service: JobService | None = None
_job_service_lock = threading.Lock()


def get_job_service() -> JobService:
    global _job_service
    if _job_service is None:
        with _job_service_lock:
            if _job_service is None:
                _job_service = JobService()
    return _job_service
