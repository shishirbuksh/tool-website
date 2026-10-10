"""SEO endpoints: sitemap.xml, robots.txt, llms.txt, IndexNow key file."""

import asyncio
import re

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
        # Sync build (YAML scans + dir listing) off the event loop.
        content = await asyncio.to_thread(sitemap_service.build_sitemap_xml)
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.exception("Failed to build sitemap.xml")
        raise HTTPException(status_code=500, detail="Failed to generate sitemap.xml") from e


@router.api_route("/sitemap-index.xml", methods=["GET", "HEAD"], response_class=Response, include_in_schema=False)
async def sitemap_index() -> Response:
    try:
        content = await asyncio.to_thread(sitemap_service.build_sitemap_index)
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.exception("Failed to build sitemap-index.xml")
        raise HTTPException(status_code=500, detail="Failed to generate sitemap-index.xml") from e


@router.api_route("/sitemap-{locale}.xml", methods=["GET", "HEAD"], response_class=Response, include_in_schema=False)
async def sitemap_locale(locale: str) -> Response:
    from app.core.i18n import is_supported_locale, normalize_locale  # noqa: PLC0415

    if not is_supported_locale(locale) or normalize_locale(locale) == "en":
        raise HTTPException(status_code=404, detail="Not found")
    try:
        content = await asyncio.to_thread(sitemap_service.build_sitemap_xml_for_locale, normalize_locale(locale))
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to build sitemap locale xml")
        raise HTTPException(status_code=500, detail="Failed to generate sitemap locale xml") from e


@router.api_route("/robots.txt", methods=["GET", "HEAD"], response_class=Response, include_in_schema=False)
async def robots_txt() -> Response:
    try:
        content = await asyncio.to_thread(sitemap_service.build_robots_txt)
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
        content = await asyncio.to_thread(sitemap_service.build_llms_txt)
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.exception("Failed to build llms.txt")
        raise HTTPException(status_code=500, detail="Failed to generate llms.txt") from e


_INDEXNOW_KEY_RE = re.compile(r"^[0-9a-fA-F]{8,128}$")


@router.api_route("/{key}.txt", methods=["GET", "HEAD"], response_class=Response, include_in_schema=False)
async def indexnow_key_file(key: str) -> Response:
    """Serve the IndexNow key file at /<KEY>.txt for Bing/Yandex ownership verification.

    Static SEO files above take precedence (registered first). Only serves when
    INDEXNOW_KEY is configured and matches; otherwise 404 (no key disclosure).
    See scripts/submit_indexnow.py for URL submission.
    """
    import hmac

    expected = (settings.INDEXNOW_KEY or "").strip()
    if expected and _INDEXNOW_KEY_RE.match(key) and hmac.compare_digest(key, expected):
        return Response(
            content=expected,
            media_type="text/plain",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    raise HTTPException(status_code=404, detail="Not found")
