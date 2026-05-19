"""Codex provider for AI Dev Squad.

This provider connects AI Dev Squad to the local Codex CLI through the
Codex tool wrapper.

Why this provider exists:
- keeps Codex-specific logic out of the agents
- supports both Plan mode and Act mode
- lets the rest of the app use a stable provider interface

Current responsibilities:
1. Create a structured implementation plan in Plan mode
2. Run the coding task in Act mode
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config.settings import Settings
from app.models.base_provider import BaseProvider
from app.tools.codex_tool import CodexTool


@dataclass
class CodexProvider(BaseProvider):
    """Provider that delegates planning and coding tasks to Codex CLI."""

    settings: Settings
    name: str = "codex"

    def plan_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Create a structured implementation plan with Codex.

        This method is used in Plan mode. It should return a structured
        result that the Orchestrator and UI can use before execution starts.

        Args:
            task: Natural language task from the user.
            repo_path: Local repository path related to the task.

        Returns:
            Structured planning result dictionary.
        """
        tool = CodexTool(settings=self.settings)
        result = tool.plan_task(task=task, repo_path=repo_path)

        # Ensure the provider name is always present in the returned payload.
        # This keeps the UI and higher-level flow consistent.
        result["provider"] = self.name
        return result

    def run_code_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Run the coding task with Codex CLI.

        This method is used in Act mode after the user has reviewed the
        plan and decided to continue.

        Args:
            task: Natural language task from the user.
            repo_path: Local repository path where code work should happen.

        Returns:
            Structured execution result dictionary.
        """
        tool = CodexTool(settings=self.settings)
        result = tool.run_code_task(task=task, repo_path=repo_path)

        # Ensure the provider name is always present in the returned payload.
        result["provider"] = self.name
        return result