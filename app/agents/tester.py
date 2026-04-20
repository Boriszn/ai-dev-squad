"""Tester agent for AI Dev Squad.

The Tester Agent runs local tests after the Developer Agent finishes.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.graph.state import WorkflowState
from app.tools.test_runner import TestRunner


@dataclass
class TesterAgent:
    """Run local test commands and return a simple summary."""

    test_runner: TestRunner

    def execute(self, state: WorkflowState) -> dict[str, object]:
        """Run the test step.

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with test results.
        """
        repo_path = state.get("repo_path", ".")
        task = state.get("task", "")

        # Pass both repo path and task text to the test runner.
        # The task text helps decide whether tests should be skipped
        # for simple non-code tasks like markdown or docs updates.
        result = self.test_runner.run(repo_path=repo_path, task=task)

        new_messages = state.get("messages", []) + [
            "Tester Agent finished the local test step.",
            result["summary"],
        ]

        return {
            "test_result": result,
            "messages": new_messages,
            "status": "tested" if result["success"] else "test_failed",
        }