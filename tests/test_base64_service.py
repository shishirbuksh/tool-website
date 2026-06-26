import pytest

from app.core.exceptions import ValidationException
from app.services.base64_service import Base64Service


class TestBase64Service:
    def test_encode(self, settings):
        svc = Base64Service(settings)
        result = svc.encode("hello world")
        assert result == "aGVsbG8gd29ybGQ="
        assert isinstance(result, str)

    def test_decode(self, settings):
        svc = Base64Service(settings)
        result = svc.decode("aGVsbG8gd29ybGQ=")
        assert result == "hello world"

    def test_roundtrip(self, settings):
        svc = Base64Service(settings)
        texts = ["", "a", "abc", "hello world", "special chars: !@#$%^&*()", "unicode: ñoño"]
        for t in texts:
            encoded = svc.encode(t)
            decoded = svc.decode(encoded)
            assert decoded == t, f"Roundtrip failed for: {t!r}"

    def test_decode_invalid(self, settings):
        svc = Base64Service(settings)
        with pytest.raises(ValidationException, match="Invalid Base64 string"):
            svc.decode("not-valid-base64!!!")
