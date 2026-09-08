import asyncio
import base64
import json
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from firebase_admin import auth

from app.auth.firebase_auth import FirebaseConfigurationError, require_ocr_admin


def token_for(project_id: str) -> str:
    def segment(value: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    return f"{segment({'alg': 'RS256'})}.{segment({'aud': project_id})}.c2ln"


def rejected(authorization: str | None) -> HTTPException:
    with pytest.raises(HTTPException) as caught:
        asyncio.run(require_ocr_admin(authorization))
    return caught.value


def test_missing_token_is_distinct() -> None:
    error = rejected(None)
    assert error.status_code == 401
    assert error.detail[0] == "TOKEN_MISSING"


def test_expired_token_is_distinct() -> None:
    app = Mock(project_id="frontend-project")
    with patch("app.auth.firebase_auth.initialize_firebase", return_value=app), patch(
        "app.auth.firebase_auth.auth.verify_id_token", side_effect=auth.ExpiredIdTokenError("expired", None)
    ):
        error = rejected("Bearer token")
    assert error.status_code == 401
    assert error.detail[0] == "TOKEN_EXPIRED"


def test_invalid_token_is_distinct() -> None:
    app = Mock(project_id="frontend-project")
    with patch("app.auth.firebase_auth.initialize_firebase", return_value=app), patch(
        "app.auth.firebase_auth.auth.verify_id_token", side_effect=auth.InvalidIdTokenError("invalid")
    ):
        error = rejected("Bearer invalid")
    assert error.status_code == 401
    assert error.detail[0] == "TOKEN_INVALID"


def test_wrong_project_token_is_distinct() -> None:
    app = Mock(project_id="expected-project")
    with patch("app.auth.firebase_auth.initialize_firebase", return_value=app), patch(
        "app.auth.firebase_auth.auth.verify_id_token", side_effect=auth.InvalidIdTokenError("invalid audience")
    ):
        error = rejected(f"Bearer {token_for('other-project')}")
    assert error.status_code == 401
    assert error.detail[0] == "TOKEN_WRONG_PROJECT"


def test_valid_user_without_ocr_right_gets_403() -> None:
    with patch("app.auth.firebase_auth.initialize_firebase", return_value=Mock()), patch(
        "app.auth.firebase_auth.auth.verify_id_token", return_value={"uid": "user"}
    ):
        error = rejected("Bearer valid")
    assert error.status_code == 403
    assert error.detail[0] == "OCR_FORBIDDEN"


def test_valid_authorized_token_returns_verified_claims() -> None:
    claims = {"uid": "user", "ocrAdmin": True}
    with patch("app.auth.firebase_auth.initialize_firebase", return_value=Mock()), patch(
        "app.auth.firebase_auth.auth.verify_id_token", return_value=claims
    ) as verify:
        assert asyncio.run(require_ocr_admin("Bearer valid")) == claims
    verify.assert_called_once_with("valid", app=verify.call_args.kwargs["app"], check_revoked=True)


def test_server_configuration_error_is_503() -> None:
    with patch("app.auth.firebase_auth.initialize_firebase", side_effect=FirebaseConfigurationError("bad config")):
        error = rejected("Bearer valid")
    assert error.status_code == 503
    assert error.detail[0] == "SERVER_AUTH_CONFIG_ERROR"
