"""환경변수 기반 앱 설정."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    app_env: str = Field(default="dev")
    app_port: int = Field(default=8000)
    frontend_origin: str = Field(default="http://localhost:3000")

    # DB
    database_url: str = Field(default=f"sqlite:///{PROJECT_ROOT / 'chord_ai.db'}")

    # Auth / JWT
    jwt_secret: str = Field(default="dev_only_change_me_to_a_long_random_string")
    jwt_alg: str = Field(default="HS256")
    jwt_expire_hours: int = Field(default=24)
    session_cookie_name: str = Field(default="chord_ai_session")

    # SMTP
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="Chord AI <noreply@example.com>")

    # Google OAuth
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_redirect_uri: str = Field(default="http://localhost:8000/auth/google/callback")

    # OpenAI (기존)
    openai_api_key: str = Field(default="")

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"

    @property
    def cookie_secure(self) -> bool:
        # dev에서는 http로 띄우므로 Secure 끔
        return not self.is_dev


@lru_cache
def get_settings() -> Settings:
    return Settings()
