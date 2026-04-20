"""Application settings for AI Dev Squad.

This module centralizes configuration loading so the rest of the code
does not need to read environment variables directly.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="AI Dev Squad", alias="APP_NAME")
    default_model_provider: str = Field(default="codex", alias="DEFAULT_MODEL_PROVIDER")
    codex_cli_command: str = Field(default="codex", alias="CODEX_CLI_COMMAND")
    local_model_name: str = Field(
        default="qwen2.5-coder:7b",
        alias="LOCAL_MODEL_NAME",
    )
    default_test_command: str = Field(default="pytest -q", alias="DEFAULT_TEST_COMMAND")
    enable_mock_tools: bool = Field(default=True, alias="ENABLE_MOCK_TOOLS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
