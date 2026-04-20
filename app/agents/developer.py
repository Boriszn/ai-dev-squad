"""Developer agent for AI Dev Squad.

The Developer Agent is responsible for sending coding requests to the
selected provider through the model router.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.graph.state import WorkflowState
from app.models.model_router import ModelRouter


@dataclass
class DeveloperAgent:
    """Handle code change requests through the active model provider."""

    model_router: ModelRouter

    def execute(self, state: WorkflowState) -> dict[str, Any]:
        """Run the developer step.

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with development results.
        """
        task = state.get("task", "")
        repo_path = state.get("repo_path", ".")
        provider_name = state.get("provider_name") or self.model_router.default_provider_name

        result = self.model_router.run_code_task(
            provider_name=provider_name,
            task=task,
            repo_path=repo_path,
        )

        new_messages = state.get("messages", []) + [
            f"Developer Agent used provider: {provider_name}",
            result["summary"],
        ]

        return {
            "provider_name": provider_name,
            "development_result": result,
            "messages": new_messages,
            "status": "developed" if result["success"] else "development_failed",
        }
