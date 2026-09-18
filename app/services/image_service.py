"""Image processing service: background removal, watermark removal with configurable MAX_IMAGE_PIXELS guard."""

import io
import logging
import re
from typing import Any

from PIL import Image, ImageColor

from app.core.config import Settings
from app.core.constants import MAX_IMAGE_PIXELS
from app.core.exceptions import ServiceError, ValidationException

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS  # ~13K x 13K

logger = logging.getLogger(__name__)

_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_VALID_INPAINT_ALGOS = {"telea", "ns"}

# ROUND-2: cache rembg sessions per-worker (model load is ~seconds + 100s MB).
# Reuse across requests instead of new_session() per request.
_SESSION_CACHE: dict[str, Any] = {}


def _get_or_create_session(model: str = "u2netp") -> Any:
    """Return cached rembg session for ``model``, creating once per worker."""
    cached = _SESSION_CACHE.get(model)
    if cached is not None:
        return cached
    from rembg import new_session  # noqa: PLC0415

    sess = new_session(model)
    _SESSION_CACHE[model] = sess
    return sess


def _check_pixels_before_decode(image_data: bytes, *, label: str = "Image") -> tuple[int, int]:
    """Validate pixel dimensions BEFORE full decode to block decompression bombs.

    Uses lazy Image.open (no full pixel load) to read dimensions first.
    """
    if not image_data:
        raise ValidationException(f"{label} data must not be empty")
    try:
        with Image.open(io.BytesIO(image_data)) as probe:
            w, h = probe.size
            # Trigger header validation without decoding full raster.
            probe.verify()
    except ValidationException:
        raise
    except Exception as e:
        raise ValidationException(f"Invalid {label.lower()} data provided") from e
    try:
        pixels = int(w) * int(h)
    except Exception:
        raise ValidationException(f"Invalid {label.lower()} dimensions")
    if pixels > MAX_IMAGE_PIXELS:
        raise ValidationException(f"{label} exceeds maximum pixel limit ({MAX_IMAGE_PIXELS})")
    return w, h


def _validate_bg_color(bg_color: str) -> str:
    """Allow ''/transparent or strict #RGB/#RRGGBB/#RRGGBBAA hex."""
    if not bg_color:
        return ""
    s = bg_color.strip()
    if s == "" or s == "transparent":
        return s
    if not _HEX_COLOR_RE.match(s):
        raise ValidationException("Invalid bg_color: must be hex like #RRGGBB or 'transparent'")
    return s


class ImageService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._rembg = None
        self._cv2 = None

    def _get_rembg(self) -> Any:
        if self._rembg is None:
            try:
                import os
                if "U2NET_HOME" not in os.environ:
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    os.environ["U2NET_HOME"] = os.path.join(base_dir, ".u2net")

                import rembg
                self._rembg = rembg
            except Exception as e:
                logger.exception("Failed to import rembg")
                raise ServiceError("Background removal library (rembg) is not available") from e
        return self._rembg

    def _get_cv2(self) -> Any:
        if self._cv2 is None:
            try:
                import cv2

                self._cv2 = cv2
            except Exception as e:
                raise ServiceError("OpenCV (cv2) is not available") from e
        return self._cv2

    def remove_background(self, image_data: bytes, bg_color: str = "", smooth_edges: bool = False) -> bytes:
        # Byte-size pre-check (equivalent of seeking file size before decode).
        try:
            max_bytes = self.settings.IMAGE_MAX_SIZE
        except Exception:
            max_bytes = 10 * 1024 * 1024
        if len(image_data) > max_bytes:
            raise ValidationException("Image exceeds maximum file size")
        # Validate before heavy decode: dimensions + bg_color hex.
        _check_pixels_before_decode(image_data, label="Image")
        bg_color = _validate_bg_color(bg_color)
        try:
            rembg = self._get_rembg()
            with Image.open(io.BytesIO(image_data)) as orig_img: input_img = orig_img.convert("RGBA")
            max_dim = 800 if smooth_edges else 2048
            if input_img.width > max_dim or input_img.height > max_dim:
                input_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            try:
                session = _get_or_create_session("u2netp")
                output_img = rembg.remove(input_img, session=session, alpha_matting=smooth_edges)
            except Exception as session_err:
                logger.warning("Fallback to default model due to session error: %s", session_err)
                output_img = rembg.remove(input_img, alpha_matting=smooth_edges)

            if bg_color and bg_color.strip() != "transparent":
                # bg_color already hex-validated; getrgb should not fail.
                rgb_color = ImageColor.getrgb(bg_color)
                bg_img = Image.new("RGBA", output_img.size, rgb_color + (255,))
                bg_img.paste(output_img, (0, 0), output_img)
                output_img = bg_img

            buf = io.BytesIO()
            output_img.save(buf, format="PNG")
            return buf.getvalue()
        except (ServiceError, ValidationException):
            raise
        except Exception as e:
            logger.exception("Failed to remove background")
            raise ServiceError("Background removal failed") from e

    def remove_watermark(self, image_data: bytes, mask_data: bytes, algorithm: str = "telea") -> bytes:
        if not image_data or not mask_data:
            raise ValidationException("Image and mask data must not be empty")
        if algorithm not in _VALID_INPAINT_ALGOS:
            raise ValidationException("Invalid algorithm: must be 'telea' or 'ns'")
        try:
            max_bytes = self.settings.IMAGE_MAX_SIZE
        except Exception:
            max_bytes = 10 * 1024 * 1024
        if len(image_data) > max_bytes or len(mask_data) > max_bytes:
            raise ValidationException("Image or mask exceeds maximum file size")

        # Pixel guard before cv2 decode (decompression-bomb protection).
        _check_pixels_before_decode(image_data, label="Image")
        _check_pixels_before_decode(mask_data, label="Mask")
        try:
            import numpy as np
        except ImportError:
            raise ServiceError("NumPy is required but not installed")
        
        cv2 = self._get_cv2()
        try:
            np_img = np.frombuffer(image_data, np.uint8)
            img_cv2 = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            np_mask = np.frombuffer(mask_data, np.uint8)
            mask_cv2 = cv2.imdecode(np_mask, cv2.IMREAD_GRAYSCALE)

            if img_cv2 is None or mask_cv2 is None:
                raise ValidationException("Invalid image or mask data provided")

            if img_cv2.shape[:2] != mask_cv2.shape[:2]:
                raise ValidationException("Mask dimensions must match image dimensions")

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
        except (ServiceError, ValidationException):
            raise
        except Exception as e:
            logger.exception("Failed to remove watermark")
            raise ServiceError("Watermark removal failed") from e

