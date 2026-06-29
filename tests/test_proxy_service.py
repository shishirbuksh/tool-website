"""Tests for ProxyService: URL validation, private-IP blocking, empty and schemeless URL handling."""

import pytest

from app.core.exceptions import ValidationException
from app.services.proxy_service import ProxyService


class TestProxyService:
    @pytest.mark.asyncio
    async def test_execute_invalid_url(self, settings):
        svc = ProxyService(settings)
        with pytest.raises(ValidationException, match="Invalid URL"):
            await svc.execute("not-a-url")

    @pytest.mark.asyncio
    async def test_execute_private_ip_blocked(self, settings):
        svc = ProxyService(settings)
        with pytest.raises(ValidationException, match="internal"):
            await svc.execute("http://127.0.0.1:8080")

    @pytest.mark.asyncio
    async def test_execute_private_ip_10_blocked(self, settings):
        svc = ProxyService(settings)
        with pytest.raises(ValidationException, match="internal"):
            await svc.execute("http://10.0.0.1:80")

    @pytest.mark.asyncio
    async def test_execute_private_ip_172_blocked(self, settings):
        svc = ProxyService(settings)
        with pytest.raises(ValidationException, match="internal"):
            await svc.execute("http://172.16.0.1:80")

    @pytest.mark.asyncio
    async def test_execute_private_ip_192_168_blocked(self, settings):
        svc = ProxyService(settings)
        with pytest.raises(ValidationException, match="internal"):
            await svc.execute("http://192.168.1.1:80")

    @pytest.mark.asyncio
    async def test_execute_empty_url(self, settings):
        svc = ProxyService(settings)
        with pytest.raises(ValidationException, match="Invalid URL"):
            await svc.execute("")

    @pytest.mark.asyncio
    async def test_execute_hostname_without_scheme(self, settings):
        svc = ProxyService(settings)
        with pytest.raises(ValidationException, match="Invalid URL"):
            await svc.execute("example.com")
