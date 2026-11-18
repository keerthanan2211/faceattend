import io

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED = {"JPEG", "PNG", "WEBP"}


class ImageError(ValueError):
    pass


def load_rgb(data: bytes, max_mb: int, max_side: int = 1280) -> np.ndarray:
    """Decodes an uploaded photo safely: checks size and type, fixes phone rotation, and downsizes."""
    if len(data) > max_mb * 1024 * 1024:
        raise ImageError(f"Images must be {max_mb} MB or smaller")
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ALLOWED:
            raise ImageError("Use a JPEG, PNG or WebP image")
        img = ImageOps.exif_transpose(img)  # phone photos are often stored sideways
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageError("That file isn't a readable image") from exc

    img.thumbnail((max_side, max_side))  # big photos slow detection without improving accuracy
    return np.asarray(img)
