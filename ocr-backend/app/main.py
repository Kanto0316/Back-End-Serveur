import time
import uuid
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.auth.firebase_auth import require_ocr_admin
from app.config import get_settings
from app.models.response import ErrorResponse, OcrResponse
from app.ocr.engine import OcrProvider, TesseractOcrProvider
from app.ocr.extractor import extract_articles
from app.ocr.preprocess import UnsupportedImageError, UnreadableImageError, preprocess_image

app = FastAPI(title="Suivi Matériel OCR", version="1.0.0")
app.state.ocr_provider = TesseractOcrProvider()
_requests: dict[str, deque[float]] = defaultdict(deque)


def error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error={"code": code, "message": message, "requestId": request.state.request_id})
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if isinstance(exc.detail, tuple):
        code, message = exc.detail
    else:
        code, message = "HTTP_ERROR", str(exc.detail)
    return error_response(request, exc.status_code, code, message)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, _exc: RequestValidationError):
    return error_response(request, 400, "INVALID_REQUEST", "Requête multipart invalide ou champ image manquant")


@app.exception_handler(Exception)
async def internal_error(request: Request, _exc: Exception):
    return error_response(request, 500, "INTERNAL_ERROR", "Erreur interne")


def enforce_rate_limit(uid: str) -> None:
    limit = get_settings().ocr_rate_limit_per_minute
    now = time.monotonic()
    bucket = _requests[uid]
    while bucket and bucket[0] <= now - 60:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail=("RATE_LIMITED", "Limite de requêtes dépassée"))
    bucket.append(now)


@app.post(
    "/v1/ocr/articles",
    response_model=OcrResponse,
    responses={code: {"model": ErrorResponse} for code in (400, 401, 403, 413, 415, 422, 429, 500)},
)
async def ocr_articles(request: Request, image: UploadFile, claims: dict = Depends(require_ocr_admin)) -> OcrResponse:
    settings = get_settings()
    enforce_rate_limit(str(claims["uid"]))
    data = await image.read(settings.max_image_bytes + 1)
    await image.close()
    if len(data) > settings.max_image_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=("IMAGE_TOO_LARGE", "Image trop grande"))
    if not data:
        raise HTTPException(status_code=400, detail=("INVALID_IMAGE", "Image vide"))
    try:
        processed = await run_in_threadpool(preprocess_image, data, settings.max_image_dimension)
    except UnsupportedImageError:
        raise HTTPException(status_code=415, detail=("UNSUPPORTED_FORMAT", "Format accepté : JPG, JPEG, PNG ou WebP")) from None
    except UnreadableImageError:
        raise HTTPException(status_code=422, detail=("UNREADABLE_IMAGE", "Image illisible")) from None
    provider: OcrProvider = request.app.state.ocr_provider
    try:
        text = await run_in_threadpool(provider.extract_text, processed)
    except Exception:
        raise HTTPException(status_code=422, detail=("OCR_FAILED", "Image illisible par le moteur OCR")) from None
    finally:
        processed.close()
    articles, warnings = extract_articles(text)
    return OcrResponse(articles=articles, warnings=warnings)
