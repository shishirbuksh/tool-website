"""SEO endpoints: sitemap.xml, robots.txt, llms.txt."""

from fastapi import APIRouter, HTTPException, Response

from app.core.config import settings
from app.core.log import get_logger
from app.services.sitemap_service import SitemapService

__all__ = ["router"]

router = APIRouter()
logger = get_logger(__name__)
sitemap_service = SitemapService(settings)


@router.api_route("/sitemap.xml", methods=["GET", "HEAD"], response_class=Response, include_in_schema=False)
async def sitemap() -> Response:
    try:
        content = sitemap_service.build_sitemap_xml()
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.exception("Failed to build sitemap.xml")
        raise HTTPException(status_code=500, detail="Failed to generate sitemap.xml") from e


@router.api_route("/robots.txt", methods=["GET", "HEAD"], response_class=Response, include_in_schema=False)
async def robots_txt() -> Response:
    try:
        content = sitemap_service.build_robots_txt()
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.exception("Failed to build robots.txt")
        raise HTTPException(status_code=500, detail="Failed to generate robots.txt") from e


@router.api_route("/llms.txt", methods=["GET", "HEAD"], response_class=Response, include_in_schema=False)
async def llms_txt() -> Response:
    try:
        content = sitemap_service.build_llms_txt()
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.exception("Failed to build llms.txt")
        raise HTTPException(status_code=500, detail="Failed to generate llms.txt") from e

