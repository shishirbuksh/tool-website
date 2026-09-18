"""Tests for CryptoService: graceful missing-dependency handling."""

import importlib.util

import pytest

from app.core.exceptions import ServiceError
from app.services.crypto_service import CryptoService


def _has_spec(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


# These tests assert the *missing-dependency* error path. When the real
# dependencies are installed the service takes the live-data path instead
# (network access), so the ServiceError expectation no longer applies — skip.
_REQUIRES_MISSING_DEPS = _has_spec("yfinance") and _has_spec("pandas")
skip_if_deps_installed = pytest.mark.skipif(
    _REQUIRES_MISSING_DEPS,
    reason="yfinance+pandas installed: service uses live-data path, not the missing-deps error",
)


class TestCryptoService:
    @skip_if_deps_installed
    @pytest.mark.asyncio
    async def test_predict_missing_deps(self, settings):
        svc = CryptoService(settings)
        with pytest.raises(ServiceError) as exc:
            await svc.predict("BTC-USD")
        msg = str(exc.value.detail)
        assert any(dep in msg for dep in ["yfinance", "rust_predictor", "Prophet", "pandas"])

    @skip_if_deps_installed
    @pytest.mark.asyncio
    async def test_analyze_trend_missing_deps(self, settings):
        svc = CryptoService(settings)
        with pytest.raises(ServiceError) as exc:
            await svc.analyze_trend("BTC-USD")
        msg = str(exc.value.detail)
        assert any(dep in msg for dep in ["yfinance", "rust_predictor", "Prophet", "pandas"])
