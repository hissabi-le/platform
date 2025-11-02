from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Sequence

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised application configuration."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Hissabi API"
    environment: Literal["development", "staging", "production"] = "development"

    database_url: str = Field(alias="DATABASE_URL")
    read_database_url: str | None = Field(default=None, alias="READ_DATABASE_URL")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")

    storage_backend: Literal["local", "s3"] = Field(default="local", alias="STORAGE_BACKEND")
    storage_local_root: str = Field(default="./data/uploads", alias="STORAGE_LOCAL_ROOT")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_bucket: str | None = Field(default=None, alias="S3_BUCKET")
    s3_access_key_id: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")

    upload_max_mb: int = Field(default=25, alias="UPLOAD_MAX_MB")
    allowed_mime_types: List[str] = Field(
        default_factory=lambda: [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "text/csv",
            "application/pdf",
        ],
        alias="ALLOWED_MIME_TYPES",
    )

    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"], alias="CORS_ORIGINS")

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="hissabi", alias="JWT_ISSUER")
    jwt_access_minutes: int = Field(default=15, alias="JWT_ACCESS_MINUTES")
    jwt_refresh_days: int = Field(default=7, alias="JWT_REFRESH_DAYS")

    rate_limit_login_per_min: int = Field(default=5, alias="RATE_LIMIT_LOGIN_PER_MIN")
    rate_limit_uploads_per_min: int = Field(default=3, alias="RATE_LIMIT_UPLOADS_PER_MIN")

    request_timeout_seconds: int = Field(default=30, alias="REQUEST_TIMEOUT_SECONDS")

    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_statement_timeout_ms: int = Field(default=60000, alias="DB_STATEMENT_TIMEOUT_MS")
    db_lock_timeout_ms: int = Field(default=5000, alias="DB_LOCK_TIMEOUT_MS")
    db_idle_tx_timeout_ms: int = Field(default=30000, alias="DB_IDLE_TX_TIMEOUT_MS")
    sqlalchemy_echo: bool = Field(default=False, alias="SQLALCHEMY_ECHO")

    clamav_host: str | None = Field(default=None, alias="CLAMAV_HOST")
    clamav_port: int = Field(default=3310, alias="CLAMAV_PORT")

    @field_validator("allowed_mime_types", "cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: Sequence[str] | str) -> List[str]:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return list(value)

    @field_validator("sqlalchemy_echo", mode="before")
    @classmethod
    def _coerce_bool(cls, value: bool | str | int) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        lowered = value.lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        return False


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


settings = get_settings()
