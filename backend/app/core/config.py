from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    SECRET_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://wellness_user:wellness_pass@localhost:5432/wellness_db"

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT (RS256) ───────────────────────────────────────────────────
    JWT_PRIVATE_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""
    JWT_PRIVATE_KEY_FILE: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── PHI Encryption ────────────────────────────────────────────────
    PHI_ENCRYPTION_KEY: str = ""

    # ── AI Providers ─────────────────────────────────────────────────
    AI_PROVIDER: Literal["anthropic", "openai", "mock"] = "anthropic"
    AI_MODEL: str = "claude-sonnet-4-6"
    AI_FALLBACK_PROVIDER: Literal["anthropic", "openai", "mock"] = "openai"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── Agora ─────────────────────────────────────────────────────────
    AGORA_APP_ID: str = ""
    AGORA_APP_CERTIFICATE: str = ""

    # ── Tap Payments ──────────────────────────────────────────────────
    TAP_SECRET_KEY: str = ""
    TAP_PUBLISHABLE_KEY: str = ""
    TAP_WEBHOOK_SECRET: str = ""

    # ── SendGrid ──────────────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@gcc-wellness.com"
    SENDGRID_FROM_NAME: str = "GCC Wellness"
    SENDGRID_TEMPLATE_BOOKING_CONFIRMATION: str = ""
    SENDGRID_TEMPLATE_BOOKING_REMINDER_24H: str = ""
    SENDGRID_TEMPLATE_BOOKING_REMINDER_1H: str = ""
    SENDGRID_TEMPLATE_WELCOME: str = ""
    SENDGRID_TEMPLATE_PAYOUT_STATEMENT: str = ""
    SENDGRID_TEMPLATE_DELETION_CONFIRMATION: str = ""

    # ── Twilio ────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # ── Firebase ─────────────────────────────────────────────────────
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""
    FIREBASE_SERVICE_ACCOUNT_FILE: str = ""

    # ── Cloudflare R2 ─────────────────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "gcc-wellness-staging"
    R2_PUBLIC_URL: str = ""

    # ── Google OAuth2 ─────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/v1/auth/google/callback"

    # ── PostHog ───────────────────────────────────────────────────────
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://app.posthog.com"

    # ── Sentry ────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_not_empty_in_prod(cls, v: str, info: object) -> str:
        # Validation happens at runtime; CI validate-env.sh catches missing vars earlier.
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
