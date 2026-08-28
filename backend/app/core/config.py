"""Environment-backed application settings.

Keeping configuration in one Pydantic settings object gives the application
and migrations the same environment selection rules. In particular, test
runs must never silently use the normal development database.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"

    postgres_db: str = "libraryos"
    postgres_test_db: str = "libraryos_test"
    postgres_user: str = "libraryos"
    postgres_password: str = "libraryos_dev_password"
    database_url: str = (
        "postgresql+psycopg://libraryos:libraryos_dev_password@"
        "localhost:5432/libraryos"
    )
    test_database_url: str = (
        "postgresql+psycopg://libraryos:libraryos_dev_password@"
        "localhost:5432/libraryos_test"
    )

    auth_secret: str = "replace_me_with_a_long_random_development_secret"
    auth_session_hours: int = Field(default=24, gt=0)
    session_cookie_name: str = "libraryos_session"

    public_api_key: str = "replace_me_public_api_key"
    public_api_rate_limit_per_minute: int = Field(default=60, gt=0)

    gemini_api_key: str = ""
    gemini_api_key_list: list[str] = Field(default_factory=list)
    gemini_model: str = ""

    upload_max_mb: int = Field(default=10, gt=0)
    upload_dir: str = "/app/uploads"
    ai_rate_limit_per_minute: int = Field(default=10, gt=0)
    online_threshold_seconds: int = Field(default=120, gt=0)
    loan_days: int = Field(default=14, gt=0)
    page_size_default: int = Field(default=20, gt=0)
    page_size_max: int = Field(default=100, gt=0)
    seed_demo_data: bool = True

    @model_validator(mode="after")
    def reject_placeholder_production_secrets(self) -> "Settings":
        """Never allow the documented development placeholders in production."""

        if self.app_env == "production":
            if self.auth_secret.startswith("replace_me") or len(self.auth_secret) < 32:
                raise ValueError("AUTH_SECRET must be replaced for production.")
            if self.public_api_key.startswith("replace_me") or len(self.public_api_key) < 16:
                raise ValueError("PUBLIC_API_KEY must be replaced for production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
