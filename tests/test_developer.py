"""Tests for Developer Agent execution in the current workflow.

This file keeps coverage intentionally small and practical. It verifies
that the developer step uses the configured default provider and returns
the expected success status in mock mode.
"""

from app.agents.developer import DeveloperAgent
from app.config.settings import Settings
from app.models.codex_provider import CodexProvider
from app.models.local_provider import LocalProvider
from app.models.model_router import ModelRouter
from app.services.task_service import build_initial_state


def build_router() -> ModelRouter:
    """Create a minimal model router used by developer tests.

    The router uses both available providers and sets Codex as the
    default so tests can assert provider selection behavior.
    """
    settings = Settings(
        ENABLE_MOCK_TOOLS=True,
        DEFAULT_MODEL_PROVIDER="codex",
    )
    return ModelRouter(
        providers={
            "codex": CodexProvider(settings=settings),
            "local": LocalProvider(settings=settings),
        },
        default_provider_name="codex",
    )


def test_developer_uses_default_provider() -> None:
    """Use the default provider when no explicit provider override exists.

    This protects against regressions where the developer step might use
    a non-default provider unexpectedly.
    """
    developer = DeveloperAgent(model_router=build_router())
    state = build_initial_state(task="Create a README note.", approval_status="approved")
    result = developer.execute(state)

    assert result["status"] == "developed"
    assert result["provider_name"] == "codex"
