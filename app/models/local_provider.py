"""Local model provider placeholder for AI Dev Squad.

This is the second provider in the architecture.
It is intentionally simple for the MVP.

Future idea:
- use a local coding model such as `qwen2.5-coder:7b`
- run it via Ollama or another local runtime
- keep the same provider interface so no graph changes are needed
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config.settings import Settings
from app.models.base_provider import BaseProvider


@dataclass
class LocalProvider(BaseProvider):
    """Placeholder provider for a future offline coding model."""

    settings: Settings
    name: str = "local"

    def run_code_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Return a placeholder result for the local model path.

        This method is intentionally not wired to a real local model yet.
        """
        model_name = self.settings.local_model_name
        return {
            "success": True,
            "summary": (
                "Local provider placeholder executed. "
                f"Future model target: {model_name}. "
                "Replace this logic later with a real offline coding call."
            ),
            "provider": self.name,
            "task": task,
            "repo_path": repo_path,
            "stdout": "",
            "stderr": "",
        }
