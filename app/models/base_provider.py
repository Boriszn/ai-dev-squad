"""Base provider interface for AI Dev Squad.

All coding providers should implement this interface so the Developer
Agent can stay independent from any specific model or tool.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Abstract base class for coding providers."""

    name: str

    @abstractmethod
    def run_code_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Run a coding task and return a structured result."""
