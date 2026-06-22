from fastapi import APIRouter, HTTPException

from app.services.job_service import get_job_service

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    svc = get_job_service()
    job = svc.get_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
