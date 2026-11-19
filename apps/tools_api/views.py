"""Tools API Views: Image Background Removal, PDF Conversion, Crypto Feeds, CORS Proxy."""

from __future__ import annotations

import io
import json
import logging
import uuid
from urllib.parse import quote
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from apps.tools_api.services.image_service import ImageService
from apps.tools_api.services.pdf_service import PDFService
from apps.tools_api.services.crypto_service import CryptoService
from apps.tools_api.services.proxy_service import ProxyService

logger = logging.getLogger(__name__)

_image_service = ImageService(settings)
_pdf_service = PDFService(settings)
_crypto_service = CryptoService(settings)
_proxy_service = ProxyService(settings)


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
    except Exception as e:
        logger.exception("Failed to remove background")
        return JsonResponse({"detail": str(e)}, status=400)


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
    except Exception as e:
        logger.exception("Failed to remove watermark")
        return JsonResponse({"detail": str(e)}, status=400)


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
    except Exception as e:
        logger.exception("Failed to convert to PDF")
        return JsonResponse({"detail": str(e)}, status=400)


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
        res = requests.get("https://api.alternative.me/fng/?limit=30", timeout=5)
        data = res.json()
        response = JsonResponse(data)
        response["Cache-Control"] = "public, max-age=300"
        return response
    except Exception:
        fallback = {"data": [{"value": "50", "value_classification": "Neutral", "timestamp": "0"}]}
        return JsonResponse(fallback)


def crypto_predict_async_view(request):
    symbol = request.GET.get("symbol", "BTC-USD")
    job_id = str(uuid.uuid4())
    return JsonResponse({"job_id": job_id, "status": "pending"})


def crypto_analyze_async_view(request):
    symbol = request.GET.get("symbol", "BTC-USD")
    job_id = str(uuid.uuid4())
    return JsonResponse({"job_id": job_id, "status": "pending"})


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
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(_crypto_service.predict(symbol))
        response = JsonResponse(res)
        response["Cache-Control"] = "public, max-age=300"
        return response
    except Exception as e:
        logger.exception("Failed to predict crypto trend")
        return JsonResponse({"detail": str(e)}, status=400)


def proxy_request_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    import asyncio
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        body = {}
    url = body.get("url") or request.POST.get("url", "")
    if not url:
        return JsonResponse({"detail": "URL parameter required"}, status=400)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(_proxy_service.execute("GET", url))
        return JsonResponse(data)
    except Exception as e:
        logger.exception("Proxy request failed")
        return JsonResponse({"detail": str(e)}, status=400)
