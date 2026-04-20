"""Tests for the model router."""

import pytest

from app.config.settings import Settings
from app.models.codex_provider import CodexProvider
from app.models.local_provider import LocalProvider
from app.models.model_router import ModelRouter


def test_model_router_returns_default_provider() -> None:
    """The router should return the default provider."""
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    router = ModelRouter(
        providers={
            "codex": CodexProvider(settings=settings),
            "local": LocalProvider(settings=settings),
        },
        default_provider_name="codex",
    )

    provider = router.get_provider()
    assert provider.name == "codex"


def test_model_router_raises_for_unknown_provider() -> None:
    """The router should reject unknown providers."""
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    router = ModelRouter(
        providers={"codex": CodexProvider(settings=settings)},
        default_provider_name="codex",
    )

    with pytest.raises(ValueError):
        router.get_provider("missing")
