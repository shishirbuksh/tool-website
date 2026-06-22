import pytest
from app.services.crypto_service import CryptoService
from app.core.exceptions import ServiceError


class TestCryptoService:
    @pytest.mark.asyncio
    async def test_predict_missing_deps(self, settings):
        svc = CryptoService(settings)
        with pytest.raises(ServiceError) as exc:
            await svc.predict("BTC-USD")
        msg = str(exc.value.detail)
        assert any(dep in msg for dep in ["yfinance", "rust_predictor", "Prophet", "pandas"])

    @pytest.mark.asyncio
    async def test_analyze_trend_missing_deps(self, settings):
        svc = CryptoService(settings)
        with pytest.raises(ServiceError) as exc:
            await svc.analyze_trend("BTC-USD")
        msg = str(exc.value.detail)
        assert any(dep in msg for dep in ["yfinance", "rust_predictor", "Prophet", "pandas"])