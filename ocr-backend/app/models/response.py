from pydantic import BaseModel, Field


class Article(BaseModel):
    code: str
    designation: str
    confidence: float = Field(ge=0, le=1)


class OcrResponse(BaseModel):
    schemaVersion: str = "1.0"
    articles: list[Article]
    warnings: list[str]


class ErrorDetail(BaseModel):
    code: str
    message: str
    requestId: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
