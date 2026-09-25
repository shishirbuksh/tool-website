"""HTTP proxy service with DNS-level private-IP blocking, request/response size caps, and header sanitization."""

import asyncio
import ipaddress
import socket
import threading
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from app.core.config import Settings

_original_getaddrinfo = socket.getaddrinfo
_dns_local = threading.local()

def _patched_getaddrinfo(
    host: Any,
    port: Any,
    family: int = 0,
    type: int = 0,
    proto: int = 0,
    flags: int = 0,
) -> list[tuple[Any, ...]]:
    forced_ip = getattr(_dns_local, 'forced_ip', None)
    target_host = getattr(_dns_local, 'target_host', None)
    if forced_ip and host == target_host:
        # Preserve address family: IPv6 literals need AF_INET6 + 4-tuple sockaddr.
        # DNS-pinned IP was validated before; this prevents TOCTOU rebinding.
        port_num = port
        if isinstance(port, str):
            try:
                port_num = int(port)
            except ValueError:
                try:
                    port_num = socket.getservbyname(port)
                except OSError:
                    port_num = 0
        try:
            ip_obj = ipaddress.ip_address(forced_ip)
            if isinstance(ip_obj, ipaddress.IPv6Address):
                return [(socket.AF_INET6, type, proto, '', (forced_ip, port_num, 0, 0))]
        except ValueError:
            pass
        return [(socket.AF_INET, type, proto, '', (forced_ip, port_num))]
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _patched_getaddrinfo
from app.core.exceptions import ServiceError, ValidationException  # noqa: E402


class ProxyService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._dns_cache: dict[str, tuple[str | None, float]] = {}
        self._dns_ttl = 300
        self._dns_maxsize = 100
        self._lock = threading.Lock()


    def _is_blocked_ip(self, ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        # Covers private/loopback/link-local + multicast/reserved/unspecified.
        # is_reserved/is_multicast also catches 0.0.0.0-adjacent and documentation ranges;
        # keep explicit 0.0.0.0 check for clarity (also matched by is_unspecified).
        if str(ip_obj) == "0.0.0.0" or str(ip_obj) == "::":
            return True
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )

    def _resolve_cached(self, hostname: str) -> str | None:
        # Normalize: strip brackets (IPv6 literals) + trailing dot.
        host = (hostname or "").strip().strip("[]").rstrip(".")
        if not host:
            return None
        # Explicit 0.0.0.0 / unspecified fast-path (decimal/octal bypass attempts
        # like 0x7f.0.0.1 still go through getaddrinfo below and get blocked there).
        if host == "0.0.0.0":
            now = time.time()
            with self._lock:
                self._dns_cache[hostname] = (None, now)
            return None
        now = time.time()
        with self._lock:
            cached = self._dns_cache.get(hostname)
        if cached and now - cached[1] < self._dns_ttl:
            return cached[0]
        # IP-literal fast path (v4 + v6): no DNS, validate directly.
        try:
            literal = ipaddress.ip_address(host)
            if self._is_blocked_ip(literal):
                with self._lock:
                    self._dns_cache[hostname] = (None, now)
                return None
            with self._lock:
                self._dns_cache[hostname] = (str(literal), now)
                self._evict_dns_cache()
            return str(literal)
        except ValueError:
            pass
        try:
            # Use getaddrinfo (not gethostbyname) so IPv6 AAAA records are
            # resolved and validated too; block if ANY returned addr is blocked.
            infos = socket.getaddrinfo(host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
            if not infos:
                raise socket.gaierror("no addr")
            first_ip: str | None = None
            for fam, _t, _p, _c, sockaddr in infos:
                ip_str = sockaddr[0]
                try:
                    ip_obj = ipaddress.ip_address(ip_str)
                except ValueError:
                    continue
                if self._is_blocked_ip(ip_obj):
                    with self._lock:
                        self._dns_cache[hostname] = (None, now)
                    return None
                if first_ip is None:
                    first_ip = ip_str
            if first_ip is None:
                raise socket.gaierror("no valid addr")
            with self._lock:
                self._dns_cache[hostname] = (first_ip, now)
                self._evict_dns_cache()
            return first_ip
        except socket.gaierror:
            with self._lock:
                self._dns_cache[hostname] = (None, now)
            return None

    def _evict_dns_cache(self) -> None:
        if len(self._dns_cache) <= self._dns_maxsize:
            return
        sorted_items = sorted(self._dns_cache.items(), key=lambda x: x[1][1])
        self._dns_cache = dict(sorted_items[self._dns_maxsize // 2:])

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        # TODO: add circuit-breaker per upstream host (trip after N consecutive
        # failures/timeouts via CacheService, cooldown before half-open retry).
        _MAX_REDIRECTS = 3
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

        headers_cleaned = {
            _strip(k): _strip(v)
            for k, v in (headers or {}).items()
            # Strip credentials + Host: forwarding user-supplied Host enables
            # cache-poisoning/SSRF quirks; requests sets Host from URL instead.
            if k.lower() not in ("authorization", "cookie", "host")
        }

        loop = asyncio.get_running_loop()

        current_url = url
        current_method = method.upper()
        current_data: bytes | None = body.encode("utf-8") if body else None
        response = None
        start_time = time.time()

        _MAX_RESP = 5_000_000

        for _redirect in range(_MAX_REDIRECTS + 1):
                parsed_current = urlparse(current_url)
                cur_scheme = parsed_current.scheme
                cur_host = parsed_current.hostname
                if not cur_host:
                    raise ValidationException("Invalid URL: missing hostname")
                if cur_scheme not in ("http", "https"):
                    raise ValidationException("Only http and https URLs are allowed")

                def _resolve(cur=cur_host):
                    return self._resolve_cached(cur)

                ip = await loop.run_in_executor(None, _resolve)
                if ip is None:
                    raise ValidationException("Access to internal networks is forbidden.")
                # Validate port AFTER SSRF check so private-IP probes report
                # "internal" (tests + security clarity) rather than port errors.
                try:
                    port = parsed_current.port
                except ValueError:
                    raise ValidationException("Invalid port in URL") from None
                if port is not None and port not in (80, 443):
                    raise ValidationException("Only ports 80/443 allowed")

                # Do NOT forward/set Host manually — requests derives it from the URL.
                kwargs = {
                    "method": current_method,
                    "url": current_url,
                    "headers": headers_cleaned,
                    "timeout": 15.0,
                    "verify": True,
                    "allow_redirects": False,
                    "stream": True,
                }
                if current_data:
                    kwargs["data"] = current_data

                def _make_request(kw=kwargs, h=cur_host, pinned=ip):
                    _dns_local.target_host = h
                    _dns_local.forced_ip = pinned
                    try:
                        resp = requests.request(**kw)
                        try:
                            # Content-Length pre-check before reading body.
                            cl = resp.headers.get("Content-Length")
                            if cl is not None:
                                try:
                                    if int(str(cl).strip()) > _MAX_RESP:
                                        resp.close()
                                        raise ValidationException("Response exceeds 5MB limit")
                                except ValidationException:
                                    raise
                                except (ValueError, TypeError):
                                    pass
                            # Cap body via iter_content (never buffer unbounded).
                            chunks: list[bytes] = []
                            total = 0
                            truncated = False
                            for chunk in resp.iter_content(chunk_size=64 * 1024):
                                if not chunk:
                                    continue
                                if total + len(chunk) > _MAX_RESP:
                                    truncated = True
                                    # Keep only up to cap.
                                    remaining = _MAX_RESP - total
                                    if remaining > 0:
                                        chunks.append(chunk[:remaining])
                                    break
                                total += len(chunk)
                                chunks.append(chunk)
                            body_bytes = b"".join(chunks)
                            resp._capped_body = body_bytes  # type: ignore[attr-defined]
                            resp._truncated = truncated  # type: ignore[attr-defined]
                            try:
                                resp.close()
                            except Exception:
                                pass
                            return resp
                        except ValidationException:
                            try:
                                resp.close()
                            except Exception:
                                pass
                            raise
                        except Exception:
                            try:
                                resp.close()
                            except Exception:
                                pass
                            raise
                    finally:
                        # Clear thread-local pin so pooled threads never leak
                        # a stale forced IP into an unrelated request.
                        _dns_local.target_host = None
                        _dns_local.forced_ip = None

                try:
                    response = await loop.run_in_executor(None, _make_request)
                except ValidationException:
                    raise
                except requests.exceptions.Timeout:
                    raise ServiceError("Request timed out after 15 seconds") from None
                except requests.exceptions.ConnectionError:
                    raise ServiceError("Failed to connect to the remote server") from None
                except requests.exceptions.RequestException:
                    raise ServiceError("Request failed") from None
                except Exception:
                    raise ServiceError("An unexpected error occurred") from None
                finally:
                    # Defense-in-depth: ensure no pin leaks if executor reuses thread
                    # after an unexpected throw before _make_request ran.
                    try:
                        _dns_local.target_host = None
                        _dns_local.forced_ip = None
                    except Exception:
                        pass

                # Manual redirect handling (allow_redirects=False above): follow max
                # _MAX_REDIRECTS, re-validating SSRF/scheme/port on each hop.
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if location:
                        if _redirect >= _MAX_REDIRECTS:
                            raise ValidationException("Too many redirects")
                        next_url = urljoin(current_url, location)
                        nxt = urlparse(next_url)
                        if nxt.scheme not in ("http", "https") or not nxt.hostname:
                            raise ValidationException("Invalid redirect target")
                        current_url = next_url
                        if response.status_code in (301, 302, 303) and current_method != "HEAD":
                            current_method = "GET"
                            current_data = None
                        continue

                end_time = time.time()

                raw_body: bytes = getattr(response, "_capped_body", b"")
                truncated = bool(getattr(response, "_truncated", False))
                try:
                    body_content = raw_body.decode("utf-8", errors="replace")
                except Exception:
                    body_content = ""
                if truncated:
                    body_content = body_content[:_MAX_RESP] + "\n[truncated: response exceeds 5MB limit]"

                # Drop Set-Cookie (session fixation via proxied cookies).
                resp_headers = {k: v for k, v in response.headers.items() if k.lower() != "set-cookie"}

                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "time_ms": int((end_time - start_time) * 1000),
                    "size_bytes": len(raw_body),
                    "headers": resp_headers,
                    "body": body_content,
                }
        raise ServiceError("An unexpected error occurred") from None
