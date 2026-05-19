"""Base provider interface for AI Dev Squad.

All coding providers should implement this interface so the rest of the
application can stay independent from any specific model, CLI, or local
runtime.

Why this interface matters:
- keeps provider logic replaceable
- separates planning from execution
- lets the app use the same flow for Codex and local models
- supports the new Plan / Act UI direction

Current provider responsibilities:
1. plan the task in a structured way
2. run the coding task and return a structured execution result
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Abstract base class for coding providers.

    Every provider must expose the same public methods so the model router
    can switch between providers without changing the higher-level flow.
    """

    name: str

    @abstractmethod
    def plan_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Create a structured implementation plan for a task.

        This method is used in Plan mode. It should analyze the task and
        return planning data that the UI can show before execution starts.

        Expected result shape can evolve, but it should normally include:
        - plan_summary
        - plan_steps
        - planned_file_changes
        - plan_notes

        Args:
            task: Natural language task from the user.
            repo_path: Local repository path related to the task.

        Returns:
            A structured planning result dictionary.
        """

    @abstractmethod
    def run_code_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Run a coding task and return a structured execution result.

        This method is used in Act mode. It should perform the provider's
        coding step and return a structured result that the Developer Agent
        can pass through the workflow.

        Args:
            task: Natural language task from the user.
            repo_path: Local repository path where code work should happen.

        Returns:
            A structured execution result dictionary.
        """