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
        self._session = requests.Session()
        self._dns_cache: dict[str, tuple[str | None, float]] = {}
        self._dns_ttl = 300

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
            return ip
        except socket.gaierror:
            self._dns_cache[hostname] = (None, now)
            return None

    async def execute(self, url: str, method: str = "GET", headers: dict = None, body: str = None) -> dict:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        if not hostname:
            raise ValidationException("Invalid URL")

        headers = {
            k.replace("\r", "").replace("\n", ""): v.replace("\r", "").replace("\n", "")
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
            response = await loop.run_in_executor(None, lambda: self._session.request(**kwargs))
            end_time = time.time()
            resp_headers = dict(response.headers)

            return {
                "status": "success",
                "status_code": response.status_code,
                "time_ms": int((end_time - start_time) * 1000),
                "size_bytes": len(response.content) if response.content else 0,
                "headers": resp_headers,
                "body": response.text,
            }
        except requests.exceptions.RequestException as e:
            raise ServiceError(f"Request failed: {str(e)}") from e
        except Exception as e:
            raise ServiceError(f"An unexpected error occurred: {str(e)}") from e
