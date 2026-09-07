from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.auth.firebase_auth import require_ocr_admin
from app.main import _requests, app
from app.ocr.engine import OcrProvider


class StubOcr(OcrProvider):
    def __init__(self, text: str):
        self.text = text

    def extract_text(self, _image: Image.Image) -> str:
        return self.text


def authorized() -> dict:
    return {"uid": "test-user", "ocrAdmin": True}


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (100, 40), "white").save(output, "PNG")
    return output.getvalue()


def setup_function() -> None:
    app.dependency_overrides.clear()
    _requests.clear()


def test_valid_image_and_successful_extraction() -> None:
    app.dependency_overrides[require_ocr_admin] = authorized
    app.state.ocr_provider = StubOcr("200LDV102350STD INTERMEDIAIRE INOX AUTO M12 INOX A2")
    response = TestClient(app).post("/v1/ocr/articles", files={"image": ("list.png", image_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json() == {
        "schemaVersion": "1.0",
        "articles": [{"code": "200LDV102350STD", "designation": "INTERMEDIAIRE INOX AUTO M12 INOX A2", "confidence": 0.92}],
        "warnings": [],
    }


def test_invalid_empty_image() -> None:
    app.dependency_overrides[require_ocr_admin] = authorized
    response = TestClient(app).post("/v1/ocr/articles", files={"image": ("empty.png", b"", "image/png")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_missing_token() -> None:
    response = TestClient(app).post("/v1/ocr/articles", files={"image": ("list.png", image_bytes(), "image/png")})
    assert response.status_code == 401
    assert response.json()["error"]["requestId"]


def test_unauthorized_user() -> None:
    async def forbidden() -> dict:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=("FORBIDDEN", "Permission OCR requise"))

    app.dependency_overrides[require_ocr_admin] = forbidden
    response = TestClient(app).post("/v1/ocr/articles", files={"image": ("list.png", image_bytes(), "image/png")})
    assert response.status_code == 403


def test_empty_extraction_has_warning() -> None:
    app.dependency_overrides[require_ocr_admin] = authorized
    app.state.ocr_provider = StubOcr("texte sans ligne article fiable")
    response = TestClient(app).post("/v1/ocr/articles", files={"image": ("list.png", image_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["articles"] == []
    assert response.json()["warnings"]


def test_file_content_not_declared_content_type_controls_format() -> None:
    app.dependency_overrides[require_ocr_admin] = authorized
    output = BytesIO()
    Image.new("RGB", (10, 10)).save(output, "BMP")
    response = TestClient(app).post("/v1/ocr/articles", files={"image": ("fake.png", output.getvalue(), "image/png")})
    assert response.status_code == 415
