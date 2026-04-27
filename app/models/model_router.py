"""Model router for AI Dev Squad.

The router hides provider selection logic from the Developer Agent.
This is where the project can switch from Codex to a local model later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.base_provider import BaseProvider


@dataclass
class ModelRouter:
    """Select and execute the active coding provider."""

    providers: dict[str, BaseProvider]
    default_provider_name: str = "codex"

    def get_provider(self, provider_name: str | None = None) -> BaseProvider:
        """Return the requested provider or the default one.

        Args:
            provider_name: Optional provider name.

        Raises:
            ValueError: If the provider name is unknown.
        """
        selected_name = (provider_name or self.default_provider_name).strip().lower()
        provider = self.providers.get(selected_name)

        if provider is None:
            raise ValueError(f"Unknown provider requested: {selected_name}")

        return provider

    def run_code_task(
        self,
        provider_name: str | None,
        task: str,
        repo_path: str,
    ) -> dict[str, Any]:
        """Run the coding task using the selected provider."""
        provider = self.get_provider(provider_name=provider_name)
        return provider.run_code_task(task=task, repo_path=repo_path)
