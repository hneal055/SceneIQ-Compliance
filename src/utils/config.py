"""
Central config (Phase 1 spine)

Rule: Anything referenced during import/app startup MUST have a default.
DB stays optional in Phase 1.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_csv(value: str) -> List[str]:
    value = (value or "").strip()
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


class Settings(BaseSettings):
    # App basics
    APP_ENV: str = Field(default="development")
    APP_HOST: str = Field(default="127.0.0.1")
    APP_PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="INFO")

    # API metadata (referenced by src.main)
    API_TITLE: str = Field(default="SceneIQ API")
    API_DESCRIPTION: str = Field(default="Phase 1 spine: rule registry + rule engine + core API endpoints.")
    API_VERSION: str = Field(default="0.1.0")
    API_PREFIX: str = Field(default="/api/0.1.0")

    # CORS (src.main expects these)
    # Defaults keep Phase 1 bootable everywhere; tighten in prod via .env.
    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    ALLOWED_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    ALLOWED_HEADERS: List[str] = Field(default_factory=lambda: ["*"])
    ALLOW_CREDENTIALS: bool = Field(default=False)

    # Back-compat / optional alt names
    CORS_ALLOW_ORIGINS: str = Field(default="*")
    CORS_ALLOW_METHODS: str = Field(default="*")
    CORS_ALLOW_HEADERS: str = Field(default="*")
    CORS_ALLOW_CREDENTIALS: Optional[bool] = Field(default=None)

    # JWT Authentication
    JWT_SECRET: str = Field(default="change-me-in-production-this-is-insecure")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_HOURS: int = Field(default=8)

    # Phase 2+ (optional for Phase 1)
    DATABASE_URL: Optional[str] = Field(default=None)

    # Phase C — AI Summarization
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)

    # Phase E — Email / SMTP
    SMTP_HOST: str = Field(default="")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_FROM: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        # If someone sets legacy CORS_* values, honor them unless explicit ALLOWED_* set.
        if self.CORS_ALLOW_ORIGINS and self.CORS_ALLOW_ORIGINS != "*" and self.ALLOWED_ORIGINS == ["*"]:
            parsed = _parse_csv(self.CORS_ALLOW_ORIGINS)
            if parsed:
                self.ALLOWED_ORIGINS = parsed

        if self.CORS_ALLOW_METHODS and self.CORS_ALLOW_METHODS != "*" and self.ALLOWED_METHODS == ["*"]:
            parsed = _parse_csv(self.CORS_ALLOW_METHODS)
            if parsed:
                self.ALLOWED_METHODS = parsed

        if self.CORS_ALLOW_HEADERS and self.CORS_ALLOW_HEADERS != "*" and self.ALLOWED_HEADERS == ["*"]:
            parsed = _parse_csv(self.CORS_ALLOW_HEADERS)
            if parsed:
                self.ALLOWED_HEADERS = parsed

        if self.CORS_ALLOW_CREDENTIALS is not None:
            self.ALLOW_CREDENTIALS = bool(self.CORS_ALLOW_CREDENTIALS)


settings = Settings()


def require_database_url() -> str:
    """Use ONLY in Phase 2+ code paths that truly need the DB."""
    if not settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required for database features. "
            "Set it in .env (see .env.example)."
        )
    return settings.DATABASE_URL

