from django.conf import settings
from django.core.exceptions import ValidationError


def validate_room_image_upload(upload):
    if not upload:
        return

    max_size = settings.RENTIFY_MAX_ROOM_IMAGE_SIZE_MB * 1024 * 1024
    if upload.size > max_size:
        raise ValidationError(f"Ảnh không được vượt quá {settings.RENTIFY_MAX_ROOM_IMAGE_SIZE_MB}MB.")

    content_type = getattr(upload, "content_type", "")
    allowed_types = set(settings.RENTIFY_ALLOWED_ROOM_IMAGE_TYPES)
    if content_type and content_type not in allowed_types:
        raise ValidationError("Chỉ hỗ trợ ảnh JPG, PNG hoặc WebP.")
