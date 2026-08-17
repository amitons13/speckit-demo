"""Configuration for the PII Guardrails service.

All tunables (model name, temperature, timeout, payload limits, default strategy)
live here and are sourced from the environment. Secrets such as the OpenAI API key
are read here and MUST never be exposed through the API surface.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PIIGUARD_",
        env_file=".env",
        extra="ignore",
    )

    # OpenAI credentials are intentionally read from the un-prefixed OPENAI_API_KEY.
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Model configuration (behind config, not hard-coded throughout the codebase).
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.0
    openai_timeout_seconds: float = 15.0

    # Guardrail behavior.
    max_payload_bytes: int = 262_144  # 256 KB
    default_redaction_strategy: str = "redact"  # redact | mask

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
