"""HTTP proxy service with DNS-level private-IP blocking, request/response size caps, and header sanitization."""

import asyncio
import ipaddress
import socket
import time
from urllib.parse import urlparse

import requests

from app.core.config import Settings
from app.core.exceptions import ServiceError, ValidationException


class ProxyService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._dns_cache: dict[str, tuple[str | None, float]] = {}
        self._dns_ttl = 300
        self._dns_maxsize = 100

    def _resolve_cached(self, hostname: str) -> str | None:
        now = time.time()
        cached = self._dns_cache.get(hostname)
        if cached and now - cached[1] < self._dns_ttl:
            return cached[0]
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                self._dns_cache[hostname] = (None, now)
                return None
            self._dns_cache[hostname] = (ip, now)
            self._evict_dns_cache()
            return ip
        except socket.gaierror:
            self._dns_cache[hostname] = (None, now)
            return None

    def _evict_dns_cache(self):
        if len(self._dns_cache) <= self._dns_maxsize:
            return
        sorted_items = sorted(self._dns_cache.items(), key=lambda x: x[1][1])
        self._dns_cache = dict(sorted_items[self._dns_maxsize // 2:])

    async def execute(self, url: str, method: str = "GET", headers: dict = None, body: str = None) -> dict:
        parsed_url = urlparse(url)
        scheme = parsed_url.scheme
        hostname = parsed_url.hostname
        if not hostname:
            raise ValidationException("Invalid URL: missing hostname")
        if scheme not in ("http", "https"):
            raise ValidationException("Only http and https URLs are allowed")
        if body and len(body) > 512_000:
            raise ValidationException("Request body exceeds 512KB limit")

        def _strip(v: str) -> str:
            return v.replace("\r", "").replace("\n", "").replace("\x00", "")

        headers = {
            _strip(k): _strip(v)
            for k, v in (headers or {}).items()
        }

        loop = asyncio.get_running_loop()

        def _resolve():
            return self._resolve_cached(hostname)

        ip = await loop.run_in_executor(None, _resolve)
        if ip is None:
            raise ValidationException("Access to internal networks is forbidden.")

        start_time = time.time()

        if "Host" not in headers and "host" not in headers:
            headers["Host"] = hostname

        kwargs = {
            "method": method.upper(),
            "url": url,
            "headers": headers,
            "timeout": 15.0,
            "verify": True,
            "allow_redirects": False,
        }

        if body:
            kwargs["data"] = body.encode("utf-8")

        try:
            response = await loop.run_in_executor(None, lambda: requests.request(**kwargs))
            end_time = time.time()

            body_content = response.text
            if len(body_content) > 5_000_000:
                body_content = body_content[:5_000_000] + "\n[truncated: response exceeds 5MB limit]"

            resp_headers = dict(response.headers)

            return {
                "status": "success",
                "status_code": response.status_code,
                "time_ms": int((end_time - start_time) * 1000),
                "size_bytes": len(response.content) if response.content else 0,
                "headers": resp_headers,
                "body": body_content,
            }
        except requests.exceptions.Timeout:
            raise ServiceError("Request timed out after 15 seconds") from None
        except requests.exceptions.ConnectionError:
            raise ServiceError("Failed to connect to the remote server") from None
        except requests.exceptions.RequestException:
            raise ServiceError("Request failed") from None
        except Exception:
            raise ServiceError("An unexpected error occurred") from None
