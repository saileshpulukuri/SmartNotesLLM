"""
Configuration module for the Flask backend.

The application reads its configuration primarily from environment
variables, with sensible defaults to make local development simple.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


class Settings:
    """Defines runtime configuration for the backend service."""

    # Flask / server
    debug: bool = False
    secret_key: str = "change-me-in-production"
    api_prefix: str = "/api"

    # Database
    database_url: str = (
        f"sqlite:///{Path(__file__).resolve().parent / 'notes.db'}"
    )

    # JWT
    jwt_secret_key: str = "replace-this-with-a-secure-random-value"
    access_token_expires_minutes: int = 120

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    llm_timeout_seconds: int = 120

    def update_from_env(self) -> None:
        """Override defaults with values from the environment."""
        import os

        self.debug = os.getenv("FLASK_DEBUG", str(self.debug)).lower() in {
            "1",
            "true",
            "yes",
        }
        self.secret_key = os.getenv("FLASK_SECRET_KEY", self.secret_key)
        self.api_prefix = os.getenv("API_PREFIX", self.api_prefix)

        self.database_url = os.getenv("DATABASE_URL", self.database_url)

        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", self.jwt_secret_key)
        self.access_token_expires_minutes = int(
            os.getenv(
                "ACCESS_TOKEN_EXPIRES_MINUTES",
                str(self.access_token_expires_minutes),
            )
        )

        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", self.ollama_base_url)
        self.ollama_model = os.getenv("OLLAMA_MODEL", self.ollama_model)
        self.llm_timeout_seconds = int(
            os.getenv("LLM_TIMEOUT_SECONDS", str(self.llm_timeout_seconds))
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of Settings populated from environment."""
    settings = Settings()
    settings.update_from_env()
    return settings


__all__ = ["Settings", "get_settings"]

