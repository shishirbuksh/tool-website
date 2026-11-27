"""Tools API Views: Image Background Removal, PDF Conversion, Crypto Feeds, CORS Proxy."""

from __future__ import annotations

import io
import json
import logging
import re
import urllib.request
import uuid
from urllib.parse import quote
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from apps.core.exceptions import AppException
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
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(_crypto_service.predict(symbol))
        response = JsonResponse(res)
        response["Cache-Control"] = "public, max-age=300"
        return response
    except Exception as e:
        logger.exception("Failed to predict crypto trend")
        return JsonResponse({"detail": str(e)}, status=400)
    finally:
        loop.close()


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
    method = (body.get("method") or "GET").upper()
    req_headers = body.get("headers")
    req_body = body.get("body")
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(
            _proxy_service.execute(
                url=url,
                method=method,
                headers=req_headers if isinstance(req_headers, dict) else None,
                body=req_body if isinstance(req_body, str) else None,
            )
        )
        return JsonResponse(data)
    except AppException as e:
        logger.warning("Proxy request error for %s: %s", url, e.detail)
        return JsonResponse({"detail": e.detail}, status=e.status_code)
    except Exception as e:
        logger.exception("Proxy request failed for %s", url)
        return JsonResponse({"detail": str(e)}, status=400)
    finally:
        loop.close()


def youtube_channel_view(request):
    """Fetch real-time public YouTube channel stats (subscribers, videos, title, avatar) without API keys."""
    import html as html_lib
    import urllib.request
    from django.core.cache import cache

    query = (request.GET.get("q") or request.GET.get("channel") or "").strip()
    if not query:
        return JsonResponse({"success": False, "message": "Query parameter required"}, status=400)

    # Normalize and sanitize handle
    m_url = re.search(r"youtube\.com/@([a-zA-Z0-9_\-\.]+)", query)
    if m_url:
        handle = m_url.group(1)
    elif query.startswith("@"):
        handle = query[1:].strip()
    else:
        handle = query.replace(" ", "").strip()

    handle = re.sub(r"[^a-zA-Z0-9_\-\.]", "", handle)
    if not handle:
        return JsonResponse({"success": False, "message": "Invalid YouTube handle format."}, status=400)

    cache_key = f"yt_ch_{handle.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    url = f"https://www.youtube.com/@{handle}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            page_bytes = response.read()
            html = page_bytes.decode("utf-8", errors="replace")

        title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        raw_title = title_match.group(1) if title_match else f"@{handle}"
        title = html_lib.unescape(raw_title)

        desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        description = html_lib.unescape(desc_match.group(1)) if desc_match else ""

        sub_match = re.search(r"([0-9\.]+[KMkm]?)\s+subscribers", html)
        subs_text = sub_match.group(1).upper() if sub_match else None

        if not subs_text:
            sub_acc = re.search(r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"', html)
            if sub_acc:
                label = sub_acc.group(1)
                m_k = re.search(r"([0-9\.]+)\s+thousand", label, re.IGNORECASE)
                m_m = re.search(r"([0-9\.]+)\s+million", label, re.IGNORECASE)
                m_b = re.search(r"([0-9\.]+)\s+billion", label, re.IGNORECASE)
                if m_m:
                    subs_text = f"{m_m.group(1)}M"
                elif m_k:
                    subs_text = f"{m_k.group(1)}K"
                elif m_b:
                    subs_text = f"{m_b.group(1)}B"

        subs_num = 0
        if subs_text:
            if subs_text.endswith("K"):
                subs_num = int(float(subs_text[:-1]) * 1000)
            elif subs_text.endswith("M"):
                subs_num = int(float(subs_text[:-1]) * 1000000)
            elif subs_text.endswith("B"):
                subs_num = int(float(subs_text[:-1]) * 1000000000)
            else:
                try:
                    subs_num = int(float(subs_text))
                except Exception:
                    subs_num = 0

        vid_match = re.search(r"([0-9\.]+[KMkm]?)\s+videos", html)
        vids_text = vid_match.group(1).upper() if vid_match else None
        vids_num = 0
        if vids_text:
            if vids_text.endswith("K"):
                vids_num = int(float(vids_text[:-1]) * 1000)
            elif vids_text.endswith("M"):
                vids_num = int(float(vids_text[:-1]) * 1000000)
            else:
                try:
                    vids_num = int(float(vids_text))
                except Exception:
                    vids_num = 0

        avatar_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        raw_avatar = avatar_match.group(1) if avatar_match else None
        avatar = None
        if raw_avatar and raw_avatar.startswith("https://") and any(d in raw_avatar for d in ["googleusercontent.com", "ggpht.com", "ytimg.com"]):
            avatar = raw_avatar

        # Niche detection
        text_corpus = (title + " " + handle + " " + description).lower()
        niche = "entertainment"
        cpm = 3.5
        shorts_pct = 35

        if any(w in text_corpus for w in ["sport", "league", "football", "cricket", "nba", "soccer", "match", "isl"]):
            niche = "sports"
            cpm = 4.0
            shorts_pct = 40
        elif any(w in text_corpus for w in ["finance", "money", "invest", "stock", "crypto", "wealth"]):
            niche = "finance"
            cpm = 20.0
            shorts_pct = 20
        elif any(w in text_corpus for w in ["tech", "code", "software", "ai", "gadget", "iphone", "hardware"]):
            niche = "tech"
            cpm = 12.0
            shorts_pct = 25
        elif any(w in text_corpus for w in ["game", "gaming", "play", "minecraft", "roblox", "fortnite"]):
            niche = "gaming"
            cpm = 3.5
            shorts_pct = 35
        elif any(w in text_corpus for w in ["science", "learn", "education", "study", "math", "physics"]):
            niche = "education"
            cpm = 10.0
            shorts_pct = 20
        elif any(w in text_corpus for w in ["fit", "fitness", "gym", "workout"]):
            niche = "fitness"
            cpm = 8.0
            shorts_pct = 35
        elif any(w in text_corpus for w in ["cook", "food", "recipe", "kitchen"]):
            niche = "food"
            cpm = 8.0
            shorts_pct = 30

        estimated_views = max(25000, int(subs_num * 1.25)) if subs_num > 0 else 100000

        res_data = {
            "success": True,
            "title": title,
            "handle": f"@{handle}",
            "subs_text": subs_text or "Growing",
            "subs_num": subs_num,
            "vids_text": vids_text or "Active",
            "vids_num": vids_num,
            "avatar": avatar,
            "niche": niche,
            "cpm": cpm,
            "shorts_pct": shorts_pct,
            "estimated_views": estimated_views,
        }
        cache.set(cache_key, res_data, 7200)
        return JsonResponse(res_data)

    except Exception as e:
        logger.warning("YouTube real-time fetch failed for %s: %s", handle, e)
        neg_data = {"success": False, "error": str(e), "handle": f"@{handle}"}
        cache.set(cache_key, neg_data, 60)
        return JsonResponse(neg_data)

