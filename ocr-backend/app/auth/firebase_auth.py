import logging

import firebase_admin
from fastapi import Header, HTTPException, status
from firebase_admin import auth, credentials, exceptions
from google.auth import jwt
from google.auth import exceptions as google_auth_exceptions

from app.config import get_settings

logger = logging.getLogger(__name__)


class FirebaseConfigurationError(RuntimeError):
    """Raised when Firebase Admin cannot be configured safely."""


def initialize_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin once using server-side credentials only."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    settings = get_settings()
    try:
        account = settings.service_account_dict()
    except (TypeError, ValueError) as exc:
        raise FirebaseConfigurationError("FIREBASE_SERVICE_ACCOUNT is not valid JSON") from exc

    account_project_id = account.get("project_id") if account else None
    if settings.firebase_project_id and account_project_id and settings.firebase_project_id != account_project_id:
        raise FirebaseConfigurationError("Firebase project IDs do not match")

    project_id = settings.firebase_project_id or account_project_id
    if not project_id:
        raise FirebaseConfigurationError("Firebase project ID is missing")

    try:
        credential = credentials.Certificate(account) if account else credentials.ApplicationDefault()
        return firebase_admin.initialize_app(credential, {"projectId": project_id})
    except (ValueError, exceptions.FirebaseError, google_auth_exceptions.GoogleAuthError) as exc:
        raise FirebaseConfigurationError("Firebase Admin initialization failed") from exc


def _reject(status_code: int, code: str, message: str) -> None:
    # Deliberately log only the classification: never credentials or request headers.
    logger.warning("OCR auth rejected: %s", code)
    raise HTTPException(status_code=status_code, detail=(code, message))


def _token_audience(token: str) -> str | None:
    """Read aud only to classify a failed verification, never to authenticate."""
    try:
        payload = jwt.decode(token, verify=False)
    except (TypeError, ValueError):
        return None
    audience = payload.get("aud")
    return audience if isinstance(audience, str) else None


async def require_ocr_admin(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        _reject(status.HTTP_401_UNAUTHORIZED, "TOKEN_MISSING", "Token Firebase manquant")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        _reject(status.HTTP_401_UNAUTHORIZED, "TOKEN_MISSING", "Token Firebase manquant")

    try:
        app = initialize_firebase()
        claims = auth.verify_id_token(token, app=app, check_revoked=True)
    except FirebaseConfigurationError:
        _reject(status.HTTP_503_SERVICE_UNAVAILABLE, "SERVER_AUTH_CONFIG_ERROR", "Authentification temporairement indisponible")
    except auth.ExpiredIdTokenError:
        _reject(status.HTTP_401_UNAUTHORIZED, "TOKEN_EXPIRED", "Token Firebase expiré")
    except (auth.RevokedIdTokenError, auth.UserDisabledError):
        _reject(status.HTTP_401_UNAUTHORIZED, "TOKEN_INVALID", "Token Firebase révoqué ou utilisateur désactivé")
    except auth.InvalidIdTokenError:
        expected_project = app.project_id
        code = "TOKEN_WRONG_PROJECT" if _token_audience(token) not in (None, expected_project) else "TOKEN_INVALID"
        _reject(status.HTTP_401_UNAUTHORIZED, code, "Token Firebase invalide")
    except (auth.CertificateFetchError, exceptions.FirebaseError, ValueError):
        _reject(status.HTTP_503_SERVICE_UNAVAILABLE, "SERVER_AUTH_CONFIG_ERROR", "Authentification temporairement indisponible")

    # Authorization is separate from authentication and relies on a verified claim.
    if claims.get("ocrAdmin") is not True:
        _reject(status.HTTP_403_FORBIDDEN, "OCR_FORBIDDEN", "Permission OCR requise")
    return claims
