"""
User endpoints — profile management and UPI ID updates.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.database.connection import get_db
from app.database.models import User
from app.services.auth_service import get_current_user
from app.services.cloudinary_service import upload_avatar

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["User"])


def _resolve_user(authorization: Optional[str], db: Session) -> User:
    """Extract the current user from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.replace("Bearer ", "")
    return get_current_user(db, token)


# ── GET /profile ─────────────────────────────────────────────────────────────

@router.get("/profile")
def get_profile(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    user = _resolve_user(authorization, db)
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "phone": user.phone,
        "email": user.email,
        "upi_id": user.upi_id,
        "trust_score": user.trust_score,
        "risk_tier": user.risk_tier,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# ── PUT /update-upi ──────────────────────────────────────────────────────────

class UpdateUpiRequest(BaseModel):
    upi_id: str


@router.put("/update-upi")
def update_upi(
    request: UpdateUpiRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Persist the user's UPI ID in PostgreSQL.
    Called after the UPI setup screen in the Flutter app.
    """
    user = _resolve_user(authorization, db)

    upi = request.upi_id.strip().lower()
    if not upi:
        raise HTTPException(status_code=400, detail="UPI ID cannot be empty")

    # Check uniqueness (another user might have the same ID)
    existing = db.query(User).filter(
        User.upi_id == upi,
        User.id != user.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="UPI ID already registered to another account")

    user.upi_id = upi
    db.commit()
    db.refresh(user)
    return {"message": "UPI ID updated", "upi_id": upi}


# ── POST /upload-avatar ───────────────────────────────────────────────────────

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/upload-avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Upload or replace the authenticated user's profile avatar.
    Accepts JPEG / PNG / WebP, max 5 MB.
    Returns the Cloudinary CDN URL stored in the user record.
    """
    user = _resolve_user(authorization, db)

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Use JPEG, PNG, or WebP.",
        )

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5 MB.")

    url = upload_avatar(data, user.user_id, file.content_type)
    if url is None:
        raise HTTPException(
            status_code=503,
            detail="Image upload service unavailable. Check Cloudinary credentials.",
        )

    user.avatar_url = url
    db.commit()
    db.refresh(user)
    return {"avatar_url": url}

    logger.info(f"UPI ID updated for user {user.user_id}: {upi}")
    return {"success": True, "upi_id": user.upi_id}
