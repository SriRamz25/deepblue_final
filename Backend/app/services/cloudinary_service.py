"""
Cloudinary service — handles profile avatar uploads.

If CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET are not set the service
returns None so callers can fail gracefully.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_configured = False


def _ensure_configured() -> bool:
    """Lazily configure Cloudinary once from app settings."""
    global _configured
    if _configured:
        return True
    try:
        from app.config import settings
        if not all([
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        ]):
            logger.warning("⚠ Cloudinary credentials not set — avatar upload disabled")
            return False
        import cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        _configured = True
        logger.info("✓ Cloudinary configured")
        return True
    except Exception as e:
        logger.error(f"✗ Cloudinary configuration failed: {e}")
        return False


def upload_avatar(file_bytes: bytes, user_id: str, content_type: str = "image/jpeg") -> Optional[str]:
    """
    Upload a profile avatar to Cloudinary.

    Args:
        file_bytes: Raw image bytes.
        user_id:    Used as the Cloudinary public_id so each user has one slot
                    (re-uploading overwrites the old image automatically).
        content_type: MIME type of the uploaded file.

    Returns:
        Secure HTTPS URL of the uploaded image, or None on failure.
    """
    if not _ensure_configured():
        return None

    try:
        import cloudinary.uploader
        import io

        result = cloudinary.uploader.upload(
            io.BytesIO(file_bytes),
            public_id=f"avatars/{user_id}",
            overwrite=True,
            resource_type="image",
            folder="sentra_pay",
            transformation=[
                {"width": 256, "height": 256, "crop": "fill", "gravity": "face"},
                {"quality": "auto", "fetch_format": "auto"},
            ],
        )
        url: str = result["secure_url"]
        logger.info(f"✓ Avatar uploaded for {user_id}: {url}")
        return url
    except Exception as e:
        logger.error(f"✗ Cloudinary upload failed for {user_id}: {e}")
        return None


def delete_avatar(user_id: str) -> bool:
    """Delete a user's avatar from Cloudinary."""
    if not _ensure_configured():
        return False
    try:
        import cloudinary.uploader
        cloudinary.uploader.destroy(f"sentra_pay/avatars/{user_id}")
        return True
    except Exception as e:
        logger.error(f"✗ Cloudinary delete failed for {user_id}: {e}")
        return False
