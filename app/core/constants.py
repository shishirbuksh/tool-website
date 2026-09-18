ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/gif"}

# Cap decompression-bomb risk: ~50MP (~7K x 7K) keeps memory bounded for rembg/PIL.
MAX_IMAGE_PIXELS = 50_000_000

__all__ = ["ALLOWED_IMAGE_MIMES", "MAX_IMAGE_PIXELS"]
