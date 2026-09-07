from io import BytesIO

from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


class UnsupportedImageError(ValueError):
    pass


class UnreadableImageError(ValueError):
    pass


def preprocess_image(data: bytes, max_dimension: int) -> Image.Image:
    """Decode in memory and normalize an image for OCR. No temporary file is used."""
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in SUPPORTED_FORMATS:
                raise UnsupportedImageError(source.format or "unknown")
            source.verify()
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            image = ImageOps.grayscale(image)
            return ImageEnhance.Contrast(image).enhance(1.5)
    except UnsupportedImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnreadableImageError("Image impossible à décoder") from exc
