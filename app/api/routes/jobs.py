"""Async job status API: poll job results by ID."""

from fastapi import APIRouter, HTTPException

from app.core.log import get_logger
from app.models.job import JobResponse
from app.services.job_service import get_job_service

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["jobs"])
logger = get_logger(__name__)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str) -> JobResponse:
    if not job_id or not job_id.strip():
        raise HTTPException(status_code=400, detail="Invalid job ID")
    try:
        svc = get_job_service()
        job = svc.get_status(job_id.strip())
    except Exception as e:
        logger.exception("Failed to get status for job %s", job_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve job status") from e
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

