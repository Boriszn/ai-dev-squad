"""Application settings for AI Dev Squad.

This module centralizes configuration loading so the rest of the code
does not need to read environment variables directly.

Why this module exists:
- keeps environment variable handling in one place
- provides typed settings for the rest of the application
- allows safe defaults for local MVP development
- ignores unrelated environment variables, such as LangSmith settings
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables.

    The settings are read from the local `.env` file and environment variables.
    Field aliases map environment variable names to Python-friendly attribute names.
    """

    # Pydantic settings configuration.
    #
    # - env_file: load values from the local `.env` file
    # - env_file_encoding: expected encoding of the env file
    # - extra="ignore": ignore unrelated env variables that are not part
    #   of this application config, for example LangSmith settings used
    #   by LangGraph Studio
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General application settings.
    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="AI Dev Squad", alias="APP_NAME")

    # Default model provider used by the model router.
    # Supported providers currently include:
    # - codex
    # - local
    default_model_provider: str = Field(
        default="codex",
        alias="DEFAULT_MODEL_PROVIDER",
    )

    # Local Codex CLI command name.
    # The default assumes `codex` is available on PATH.
    codex_cli_command: str = Field(
        default="codex",
        alias="CODEX_CLI_COMMAND",
    )

    # Placeholder local model name for future offline mode.
    # Example target later: Ollama or another local model runtime.
    local_model_name: str = Field(
        default="qwen2.5-coder:7b",
        alias="LOCAL_MODEL_NAME",
    )

    # Default local test command used by the Tester Agent.
    default_test_command: str = Field(
        default="pytest -q",
        alias="DEFAULT_TEST_COMMAND",
    )

    # Mock mode flag for safe local testing.
    # When enabled, external tools like Codex and test execution
    # can return mock responses instead of running real commands.
    enable_mock_tools: bool = Field(
        default=True,
        alias="ENABLE_MOCK_TOOLS",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings.

    Settings are loaded once and then reused, which avoids reading and
    parsing environment variables multiple times during the same run.
    """
    return Settings()