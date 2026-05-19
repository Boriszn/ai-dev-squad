"""Tests for model router provider selection behavior.

These tests keep router coverage focused and readable: they confirm that
the default provider is returned when requested implicitly, and that
unknown provider names fail with a clear error.
"""

import pytest

from app.config.settings import Settings
from app.models.codex_provider import CodexProvider
from app.models.local_provider import LocalProvider
from app.models.model_router import ModelRouter


def test_model_router_returns_default_provider() -> None:
    """Return the configured default provider when no name is passed.

    This protects the default provider contract used by workflow agents.
    """
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
    """Raise a ValueError for unknown provider names.

    This protects against silent fallback behavior for invalid provider IDs.
    """
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    router = ModelRouter(
        providers={"codex": CodexProvider(settings=settings)},
        default_provider_name="codex",
    )

    with pytest.raises(ValueError):
        router.get_provider("missing")
