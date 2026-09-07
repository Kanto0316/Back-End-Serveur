import firebase_admin
from fastapi import Header, HTTPException, status
from firebase_admin import auth, credentials

from app.config import get_settings


def initialize_firebase() -> None:
    """Initialize Firebase Admin once, without using any Firebase client API."""
    if firebase_admin._apps:
        return
    settings = get_settings()
    options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
    account = settings.service_account_dict()
    credential = credentials.Certificate(account) if account else credentials.ApplicationDefault()
    firebase_admin.initialize_app(credential, options)


async def require_ocr_admin(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=("UNAUTHENTICATED", "Token Firebase manquant ou invalide"))
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=("UNAUTHENTICATED", "Token Firebase manquant ou invalide"))
    try:
        initialize_firebase()
        claims = auth.verify_id_token(token, check_revoked=True)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=("UNAUTHENTICATED", "Token Firebase manquant ou invalide")) from None
    # Authorization depends only on a server-verified custom claim.
    if claims.get("ocrAdmin") is not True:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=("FORBIDDEN", "Permission OCR requise"))
    return claims
