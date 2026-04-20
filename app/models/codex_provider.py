"""Codex provider for AI Dev Squad.

This provider calls the local Codex CLI through a tool wrapper.
It is the default coding provider for the MVP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config.settings import Settings
from app.models.base_provider import BaseProvider
from app.tools.codex_tool import CodexTool


@dataclass
class CodexProvider(BaseProvider):
    """Provider that delegates coding tasks to Codex CLI."""

    settings: Settings
    name: str = "codex"

    def run_code_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Run the coding task with Codex CLI.

        The tool can operate in mock mode for safe early testing.
        """
        tool = CodexTool(settings=self.settings)
        return tool.run(task=task, repo_path=repo_path)
