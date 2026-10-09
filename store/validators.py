"""Validation for uploaded product images: size, real image content, allowed format."""
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _is_new_upload(file):
    # Files already saved in storage are marked "committed"; only inspect fresh uploads.
    return getattr(file, "_committed", True) is False


def validate_image_size(file):
    if not _is_new_upload(file):
        return
    limit = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f"Image is too large. The maximum size is {settings.MAX_IMAGE_UPLOAD_MB} MB.")


def validate_image_content(file):
    if not _is_new_upload(file):
        return
    try:
        file.seek(0)
        with Image.open(file) as img:
            img_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ValidationError("The uploaded file is not a valid image.")
    finally:
        try:
            file.seek(0)
        except Exception:  # pragma: no cover
            pass
    if img_format not in ALLOWED_FORMATS:
        raise ValidationError("Unsupported image format. Please upload a JPEG, PNG or WebP image.")
