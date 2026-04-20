"""Tests for the Developer Agent."""

from app.agents.developer import DeveloperAgent
from app.config.settings import Settings
from app.models.codex_provider import CodexProvider
from app.models.local_provider import LocalProvider
from app.models.model_router import ModelRouter
from app.services.task_service import build_initial_state


def build_router() -> ModelRouter:
    """Create a simple router for tests."""
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
    """The Developer Agent should use the default provider."""
    developer = DeveloperAgent(model_router=build_router())
    state = build_initial_state(task="Create a README note.", approval_status="approved")
    result = developer.execute(state)

    assert result["status"] == "developed"
    assert result["provider_name"] == "codex"
