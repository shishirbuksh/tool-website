import base64

from app.core.config import Settings
from app.core.exceptions import ValidationException


class Base64Service:
    def __init__(self, settings: Settings):
        self.settings = settings

    def encode(self, text: str) -> str:
        encoded_bytes = base64.b64encode(text.encode("utf-8"))
        return encoded_bytes.decode("utf-8")

    def decode(self, text: str) -> str:
        try:
            decoded_bytes = base64.b64decode(text.encode("utf-8"))
            return decoded_bytes.decode("utf-8")
        except Exception as e:
            raise ValidationException("Invalid Base64 string") from e
