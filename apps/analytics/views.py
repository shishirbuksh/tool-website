"""Analytics Views: Track and Top Counts."""

from __future__ import annotations

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from apps.analytics.services import track, get_counts


def _is_internal(request) -> bool:
    remote_addr = request.META.get("REMOTE_ADDR", "").strip()
    if remote_addr in ("127.0.0.1", "::1"):
        real_ip = (request.headers.get("x-real-ip") or request.META.get("HTTP_X_REAL_IP", "")).strip()
        if real_ip:
            return real_ip in ("127.0.0.1", "::1", "localhost")
        return True
    return False


@csrf_exempt
def track_view(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        body = {}
    name = body.get("name") or request.POST.get("name", "")
    category = body.get("category") or request.POST.get("category", "page_view")
    success = track(name, category)
    return JsonResponse({"status": "ok" if success else "dropped", "ok": bool(success)})


def top_counts(request):
    if not _is_internal(request):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    try:
        limit = int(request.GET.get("limit", 20))
    except ValueError:
        limit = 20
    counts = get_counts(limit=limit)
    response = JsonResponse(counts)
    response["Cache-Control"] = "public, max-age=60"
    return response
