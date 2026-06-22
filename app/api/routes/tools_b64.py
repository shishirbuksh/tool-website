from fastapi import APIRouter, Form

from app.core.config import settings
from app.core.log import get_logger
from app.services.base64_service import Base64Service

router = APIRouter(prefix="/api", tags=["Base64"])
base64_service = Base64Service(settings)
logger = get_logger(__name__)


@router.get("/ping")
def ping():
    return {"ping": "pong"}


@router.post("/base64-encode")
async def base64_encode(text: str = Form(...)):
    return {"result": base64_service.encode(text)}


@router.post("/base64-decode")
async def base64_decode(text: str = Form(...)):
    return {"result": base64_service.decode(text)}
