from __future__ import annotations

from functools import lru_cache
from typing import Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the analytics worker."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="analytics-worker", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(default="sqlite+aiosqlite:///tmp/analytics_worker.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")

    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")
    sqlalchemy_echo: bool = Field(default=False, alias="SQLALCHEMY_ECHO")

    analytics_cache_ttl_seconds: int = Field(default=900, alias="ANALYTICS_CACHE_TTL_SECONDS")
    analytics_range_windows: Dict[str, int] = Field(
        default_factory=lambda: {"1m": 30, "3m": 90, "6m": 180, "1y": 365},
        alias="ANALYTICS_RANGE_WINDOWS",
    )
    analytics_query_batch_size: int = Field(default=2000, alias="ANALYTICS_QUERY_BATCH_SIZE")
    analytics_backfill_enabled: bool = Field(default=True, alias="ANALYTICS_BACKFILL_ENABLED")
    analytics_job_ttl_seconds: int = Field(default=86_400, alias="ANALYTICS_JOB_TTL_SECONDS")

    worker_concurrency: int = Field(default=2, alias="WORKER_CONCURRENCY")
    worker_prefetch_multiplier: int = Field(default=1, alias="WORKER_PREFETCH_MULTIPLIER")

    healthcheck_interval_seconds: int = Field(default=60, alias="HEALTHCHECK_INTERVAL_SECONDS")

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @field_validator("analytics_range_windows", mode="before")
    @classmethod
    def _parse_windows(cls, value: Dict[str, int] | str) -> Dict[str, int]:
        if isinstance(value, dict):
            return {str(k): int(v) for k, v in value.items()}
        result: Dict[str, int] = {}
        for chunk in str(value).split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "=" not in chunk:
                continue
            range_key, raw_days = chunk.split("=", 1)
            range_key = range_key.strip()
            try:
                result[range_key] = int(raw_days.strip())
            except ValueError:
                continue
        return result or {"1m": 30, "3m": 90, "6m": 180, "1y": 365}

    @field_validator("sqlalchemy_echo", mode="before")
    @classmethod
    def _parse_bool(cls, value: bool | str | int) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        lowered = str(value).strip().lower()
        return lowered in {"1", "true", "yes", "on"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


settings = get_settings()
