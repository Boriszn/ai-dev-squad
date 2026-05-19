"""Model router for AI Dev Squad.

The router hides provider selection logic from the rest of the app.
It lets the workflow switch between providers like Codex and local
models without changing higher-level logic.

Why this file matters:
- keeps provider lookup in one place
- separates planning calls from execution calls
- supports the Plan / Act UI direction
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

        Returns:
            The selected provider instance.

        Raises:
            ValueError: If the provider name is unknown.
        """
        selected_name = (provider_name or self.default_provider_name).strip().lower()
        provider = self.providers.get(selected_name)

        if provider is None:
            raise ValueError(f"Unknown provider requested: {selected_name}")

        return provider

    def plan_task(
        self,
        provider_name: str | None,
        task: str,
        repo_path: str,
    ) -> dict[str, Any]:
        """Run the planning step using the selected provider.

        This method is used in Plan mode. It asks the provider to
        return a structured plan before any code execution starts.

        Args:
            provider_name: Optional provider name.
            task: Natural language task from the user.
            repo_path: Local repository path related to the task.

        Returns:
            Structured planning result from the provider.
        """
        provider = self.get_provider(provider_name=provider_name)
        return provider.plan_task(task=task, repo_path=repo_path)

    def run_code_task(
        self,
        provider_name: str | None,
        task: str,
        repo_path: str,
    ) -> dict[str, Any]:
        """Run the coding task using the selected provider.

        This method is used in Act mode after the user has already
        reviewed the plan and decided to continue.

        Args:
            provider_name: Optional provider name.
            task: Natural language task from the user.
            repo_path: Local repository path where coding work should happen.

        Returns:
            Structured execution result from the provider.
        """
        provider = self.get_provider(provider_name=provider_name)
        return provider.run_code_task(task=task, repo_path=repo_path)