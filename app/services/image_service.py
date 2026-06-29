"""Image processing service: background removal, watermark removal with configurable MAX_IMAGE_PIXELS guard."""

import io
import logging

import numpy as np
from PIL import Image, ImageColor

from app.core.config import Settings
from app.core.exceptions import ServiceError, ValidationException

# Decompression bomb protection
Image.MAX_IMAGE_PIXELS = 178_000_000  # ~13K x 13K

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._rembg = None
        self._cv2 = None

    def _get_rembg(self):
        if self._rembg is None:
            try:
                import os
                if "U2NET_HOME" not in os.environ:
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    os.environ["U2NET_HOME"] = os.path.join(base_dir, ".u2net")
                    
                import rembg
                self._rembg = rembg
            except Exception as e:
                logger.error("Failed to import rembg", exc_info=True)
                raise ServiceError("Background removal library (rembg) is not available") from e
        return self._rembg

    def _get_cv2(self):
        if self._cv2 is None:
            try:
                import cv2

                self._cv2 = cv2
            except Exception as e:
                raise ServiceError("OpenCV (cv2) is not available") from e
        return self._cv2

    def remove_background(self, image_data: bytes, bg_color: str = "", smooth_edges: bool = False) -> bytes:
        try:
            rembg = self._get_rembg()
            input_img = Image.open(io.BytesIO(image_data)).convert("RGBA")
            max_dim = 800 if smooth_edges else 2048
            if input_img.width > max_dim or input_img.height > max_dim:
                input_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            try:
                from rembg import new_session

                session = new_session("u2netp")
                output_img = rembg.remove(input_img, session=session, alpha_matting=smooth_edges)
            except Exception as session_err:
                logger.warning("Fallback to default model due to session error: %s", session_err)
                output_img = rembg.remove(input_img, alpha_matting=smooth_edges)

            if bg_color and bg_color.strip() != "transparent":
                try:
                    rgb_color = ImageColor.getrgb(bg_color)
                    bg_img = Image.new("RGBA", output_img.size, rgb_color + (255,))
                    bg_img.paste(output_img, (0, 0), output_img)
                    output_img = bg_img
                except Exception as e:
                    logger.error("Color error: %s", e)

            buf = io.BytesIO()
            output_img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            logger.error("Failed to remove background: %s", e, exc_info=True)
            raise ServiceError(f"Background removal failed: {str(e)}") from e

    def remove_watermark(self, image_data: bytes, mask_data: bytes, algorithm: str = "telea") -> bytes:
        cv2 = self._get_cv2()
        np_img = np.frombuffer(image_data, np.uint8)
        img_cv2 = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        np_mask = np.frombuffer(mask_data, np.uint8)
        mask_cv2 = cv2.imdecode(np_mask, cv2.IMREAD_GRAYSCALE)

        if img_cv2 is None or mask_cv2 is None:
            raise ValidationException("Invalid image or mask data provided")

        max_dim = 2048
        h, w = img_cv2.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w, new_h = int(w * scale), int(h * scale)
            img_cv2 = cv2.resize(img_cv2, (new_w, new_h), interpolation=cv2.INTER_AREA)
            mask_cv2 = cv2.resize(mask_cv2, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

        flag = cv2.INPAINT_NS if algorithm == "ns" else cv2.INPAINT_TELEA
        restored = cv2.inpaint(img_cv2, mask_cv2, inpaintRadius=3, flags=flag)

        is_success, buffer = cv2.imencode(".png", restored)
        if not is_success:
            raise ServiceError("Failed to encode image")
        return buffer.tobytes()
