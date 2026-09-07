import json
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded exclusively from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    firebase_project_id: str | None = Field(default=None, alias="FIREBASE_PROJECT_ID")
    firebase_service_account: str | None = Field(default=None, alias="FIREBASE_SERVICE_ACCOUNT")
    max_image_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_IMAGE_BYTES")
    max_image_dimension: int = Field(default=2400, alias="MAX_IMAGE_DIMENSION")
    ocr_rate_limit_per_minute: int = Field(default=30, alias="OCR_RATE_LIMIT_PER_MINUTE")

    def service_account_dict(self) -> dict | None:
        if not self.firebase_service_account:
            return None
        return json.loads(self.firebase_service_account)


@lru_cache
def get_settings() -> Settings:
    return Settings()
