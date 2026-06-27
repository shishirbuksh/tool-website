import io

import qrcode

from app.core.config import Settings


class QRService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(
        self, data: str, fg_color: str = "black", bg_color: str = "white", error_correction: str = "L"
    ) -> bytes:
        ec_map = {
            "L": qrcode.constants.ERROR_CORRECT_L,
            "M": qrcode.constants.ERROR_CORRECT_M,
            "Q": qrcode.constants.ERROR_CORRECT_Q,
            "H": qrcode.constants.ERROR_CORRECT_H,
        }
        ec_level = ec_map.get(error_correction.upper(), qrcode.constants.ERROR_CORRECT_L)

        qr = qrcode.QRCode(version=1, error_correction=ec_level, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fg_color, back_color=bg_color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
