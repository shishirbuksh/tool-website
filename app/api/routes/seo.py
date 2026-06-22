from fastapi import APIRouter, Response

from app.core.config import settings
from app.services.sitemap_service import SitemapService

router = APIRouter()
sitemap_service = SitemapService(settings)


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    return Response(content=sitemap_service.build_sitemap_xml(), media_type="application/xml")


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return Response(content=sitemap_service.build_robots_txt(), media_type="text/plain")


@router.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    return Response(content=sitemap_service.build_llms_txt(), media_type="text/plain")
