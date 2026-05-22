"""
Application settings loaded from environment variables / .env file.

Uses Pydantic BaseSettings for automatic validation and type coercion.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # ── Application ──
    APP_NAME: str = "AuthForge"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOG_LEVEL: str = "INFO"

    # ── Database ──
    DATABASE_URL: str

    # ── Redis ──
    REDIS_URL: str

    # ── Celery ──
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # ── Email ──
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_FROM: str
    MAIL_USE_TLS: bool = False        # True for production SMTP (SendGrid, SES, etc.)
    MAIL_USERNAME: str = ""           # SMTP auth username (empty for MailHog)
    MAIL_PASSWORD: str = ""           # SMTP auth password (empty for MailHog)

    # ── OAuth ──
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # ── Security ──
    RATE_LIMIT_LOGIN: int = 5
    RATE_LIMIT_SIGNUP: int = 3
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]  # Restrict by default

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
