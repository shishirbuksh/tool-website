import pytest

from app.models.job import JobStatus
from app.services.job_service import JobService


class TestJobService:
    @pytest.mark.asyncio
    async def test_submit_and_poll(self):
        svc = JobService()

        async def dummy():
            return 42

        resp = svc.submit("test", dummy)
        assert resp.job_id is not None
        assert resp.status in (JobStatus.PENDING, JobStatus.RUNNING)

        import asyncio
        await asyncio.sleep(0.01)

        poll = svc.get_status(resp.job_id)
        assert poll is not None
        assert poll.status == JobStatus.DONE
        assert poll.result == 42

    @pytest.mark.asyncio
    async def test_submit_error(self):
        svc = JobService()

        async def failing():
            raise ValueError("boom")

        resp = svc.submit("fail", failing)
        import asyncio
        await asyncio.sleep(0.01)

        poll = svc.get_status(resp.job_id)
        assert poll is not None
        assert poll.status == JobStatus.ERROR
        assert "boom" in poll.error

    def test_get_status_not_found(self):
        svc = JobService()
        result = svc.get_status("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_jobs(self):
        svc = JobService()
        jobs = []
        for i in range(5):
            async def make_job(val=i):
                return val * 2
            resp = svc.submit(f"job_{i}", make_job)
            jobs.append(resp)

        import asyncio
        await asyncio.sleep(0.02)

        for i, resp in enumerate(jobs):
            poll = svc.get_status(resp.job_id)
            assert poll is not None
            assert poll.status == JobStatus.DONE
            assert poll.result == i * 2
