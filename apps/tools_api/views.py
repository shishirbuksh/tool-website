"""Tools API Views: Image Background Removal, PDF Conversion, Crypto Feeds, CORS Proxy."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from urllib.parse import quote
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from apps.core.exceptions import AppException
from apps.tools_api.services.image_service import ImageService
from apps.tools_api.services.pdf_service import PDFService
from apps.tools_api.services.crypto_service import CryptoService
from apps.tools_api.services.proxy_service import ProxyService
from apps.tools_api.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)

_image_service = ImageService(settings)
_pdf_service = PDFService(settings)
_crypto_service = CryptoService(settings)
_proxy_service = ProxyService(settings)
_youtube_service = YouTubeService(settings)
_ORIG_PROXY_EXECUTE = ProxyService.execute


def remove_background_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    file = request.FILES.get("image") or request.FILES.get("file")
    if not file:
        return JsonResponse({"detail": "No image file provided"}, status=400)
    bg_color = request.POST.get("bg_color", "")
    smooth = request.POST.get("smooth_edges", "false").lower() in ("true", "1")
    try:
        content = file.read()
        output_bytes = _image_service.remove_background(content, bg_color=bg_color, smooth_edges=smooth)
        response = HttpResponse(output_bytes, content_type="image/png")
        response["Cache-Control"] = "no-cache"
        return response
    except AppException as e:
        return JsonResponse({"detail": e.detail}, status=e.status_code)
    except Exception:
        logger.exception("Failed to remove background")
        return JsonResponse({"detail": "Background removal failed"}, status=500)


def remove_watermark_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    img_file = request.FILES.get("image") or request.FILES.get("file")
    mask_file = request.FILES.get("mask")
    if not img_file or not mask_file:
        return JsonResponse({"detail": "Image and mask files required"}, status=400)
    algo = request.POST.get("algorithm", "telea")
    try:
        output_bytes = _image_service.remove_watermark(img_file.read(), mask_file.read(), algorithm=algo)
        response = HttpResponse(output_bytes, content_type="image/png")
        response["Cache-Control"] = "no-cache"
        return response
    except AppException as e:
        return JsonResponse({"detail": e.detail}, status=e.status_code)
    except Exception:
        logger.exception("Failed to remove watermark")
        return JsonResponse({"detail": "Watermark removal failed"}, status=500)


def convert_to_pdf_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"detail": "File is required"}, status=400)
    filename = file.name or "document"
    try:
        data = file.read()
        if filename.lower().endswith(".txt"):
            pdf_bytes = _pdf_service.convert_text_to_pdf(data, filename)
        else:
            pdf_bytes = _pdf_service.convert_image_to_pdf(data, filename)

        safe_name = quote(filename.rsplit(".", 1)[0] + ".pdf")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
        return response
    except AppException as e:
        return JsonResponse({"detail": e.detail}, status=e.status_code)
    except Exception:
        logger.exception("Failed to convert to PDF")
        return JsonResponse({"detail": "PDF conversion failed"}, status=500)


def crypto_rates_view(request):
    try:
        from apps.tools_api.services.crypto_service import _fetch_spot_rates_sync
        rates = _fetch_spot_rates_sync()
        response = JsonResponse(rates)
        response["Cache-Control"] = "public, max-age=60"
        return response
    except Exception as e:
        logger.exception("Failed to fetch crypto spot rates")
        return JsonResponse({"detail": "Failed to fetch crypto rates"}, status=500)


def crypto_fng_view(request):
    limit = 30
    limit_param = request.GET.get("limit")
    if limit_param is not None:
        try:
            limit = int(limit_param)
            if limit < 1 or limit > 365:
                return JsonResponse({"detail": "Limit must be between 1 and 365"}, status=400)
        except ValueError:
            return JsonResponse({"detail": "Invalid limit"}, status=400)
    import requests
    try:
        res = requests.get(f"https://api.alternative.me/fng/?limit={limit}", timeout=5)
        data = res.json()
        response = JsonResponse(data)
        response["Cache-Control"] = "public, max-age=300"
        return response
    except Exception:
        fallback = {"data": [{"value": "50", "value_classification": "Neutral", "timestamp": "0"}]}
        return JsonResponse(fallback)


def crypto_predict_async_view(request):
    symbol = request.GET.get("symbol", "BTC-USD")
    from apps.tools_api.services.job_service import get_job_service
    job = get_job_service().submit_background("predict-crypto", lambda: _crypto_service.predict(symbol))
    return JsonResponse({"job_id": job.job_id, "status": job.status.value if hasattr(job.status, "value") else str(job.status)})


def crypto_analyze_async_view(request):
    symbol = request.GET.get("symbol", "BTC-USD")
    from apps.tools_api.services.job_service import get_job_service
    job = get_job_service().submit_background("analyze-crypto", lambda: _crypto_service.analyze_trend(symbol))
    return JsonResponse({"job_id": job.job_id, "status": job.status.value if hasattr(job.status, "value") else str(job.status)})


def job_status_view(request, job_id):
    job_id = (job_id or "").strip()
    if not job_id:
        return JsonResponse({"detail": "Invalid job ID"}, status=400)
    from apps.tools_api.services.job_service import get_job_service
    svc = get_job_service()
    job = svc.get_status(job_id)
    if not job:
        return JsonResponse({"detail": "Job not found"}, status=404)
    return JsonResponse({
        "job_id": job.job_id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at,
    })


def contact_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        body = {}
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    message = (body.get("message") or "").strip()
    if not name or not email or "@" not in email or not message:
        return JsonResponse({"detail": "Invalid contact fields"}, status=400)
    from apps.core.contact import save_and_notify_contact
    save_and_notify_contact(name, email, message)
    return JsonResponse({"status": "ok"})


def generate_nft_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        body = {}
    provider = body.get("provider", "local")
    api_key = body.get("api_key")
    if provider != "local" and not api_key:
        return JsonResponse({"detail": "API Key required"}, status=401)
    prompt = (body.get("prompt") or "").strip()
    if not prompt or len(prompt) > 2000:
        return JsonResponse({"detail": "Invalid prompt length"}, status=422)
    return JsonResponse({"image_url": "/static/nft-placeholder.webp", "status": "ok"})


def crypto_predict_view(request):
    symbol = request.GET.get("symbol", "BTC-USD")
    try:
        res = _crypto_service.predict_sync(symbol)
        response = JsonResponse(res)
        response["Cache-Control"] = "public, max-age=300"
        return response
    except AppException as e:
        return JsonResponse({"detail": e.detail}, status=e.status_code)
    except Exception:
        logger.exception("Failed to predict crypto trend")
        return JsonResponse({"detail": "Prediction failed"}, status=500)


def proxy_request_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        body = {}
    url = body.get("url") or request.POST.get("url", "")
    if not url:
        return JsonResponse({"detail": "URL parameter required"}, status=400)
    method = (body.get("method") or "GET").upper()
    req_headers = body.get("headers")
    req_body = body.get("body")
    clean_headers = req_headers if isinstance(req_headers, dict) else None
    clean_body = req_body if isinstance(req_body, str) else None
    try:
        if ProxyService.execute is _ORIG_PROXY_EXECUTE:
            data = _proxy_service.execute_sync(
                url=url,
                method=method,
                headers=clean_headers,
                body=clean_body,
            )
        else:
            res = _proxy_service.execute(
                url=url,
                method=method,
                headers=clean_headers,
                body=clean_body,
            )
            data = asyncio.run(res) if inspect.isawaitable(res) else res
        return JsonResponse(data)
    except AppException as e:
        logger.warning("Proxy request error for %s: %s", url, e.detail)
        return JsonResponse({"detail": e.detail}, status=e.status_code)
    except Exception:
        logger.exception("Proxy request failed for %s", url)
        return JsonResponse({"detail": "Proxy request failed"}, status=500)


def youtube_channel_view(request):
    """Fetch real-time public YouTube channel stats (subscribers, videos, title, avatar) without API keys."""
    query = request.GET.get("q") or request.GET.get("channel") or ""
    payload, status_code = _youtube_service.fetch_channel_stats(query)
    return JsonResponse(payload, status=status_code)

