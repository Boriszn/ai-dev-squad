"""Application settings for AI Dev Squad.

This module centralizes configuration loading so the rest of the code
does not need to read environment variables directly.

Why this module exists:
- keeps environment variable handling in one place
- provides typed settings for the rest of the application
- allows safe defaults for local development
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

    # -------------------------------------------------------------------------
    # General application settings
    # -------------------------------------------------------------------------

    # Environment name, for example local/dev/test.
    app_env: str = Field(default="local", alias="APP_ENV")

    # Human-readable application name.
    app_name: str = Field(default="AI Dev Squad", alias="APP_NAME")

    # -------------------------------------------------------------------------
    # Model provider settings
    # -------------------------------------------------------------------------

    # Default model provider used by the model router.
    # Supported providers currently include:
    # - codex
    # - local
    default_model_provider: str = Field(
        default="codex",
        alias="DEFAULT_MODEL_PROVIDER",
    )

    # Codex CLI command name.
    # The default assumes `codex` is available on PATH.
    codex_cli_command: str = Field(
        default="codex",
        alias="CODEX_CLI_COMMAND",
    )

    # Local model name for the offline/local provider.
    # Example:
    # qwen2.5-coder:7b
    local_model_name: str = Field(
        default="qwen2.5-coder:7b",
        alias="LOCAL_MODEL_NAME",
    )

    # Base URL of the local Ollama runtime.
    # The local provider uses this endpoint to call the local model.
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )

    # -------------------------------------------------------------------------
    # Test and execution settings
    # -------------------------------------------------------------------------

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