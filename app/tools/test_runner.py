"""Local test runner for AI Dev Squad.

This module contains the low-level wrapper that runs local tests.
It is used by the Tester Agent.

Main behavior:
- Supports mock mode for early safe testing
- Runs a local test command, by default `pytest -q`
- Treats "no tests ran" as OK for simple tasks
- Skips tests for clearly non-code tasks like markdown/doc updates
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import Any

from app.config.settings import Settings


@dataclass
class TestRunner:
    """Run local tests for the current repository."""

    settings: Settings

    def run(self, repo_path: str, task: str = "") -> dict[str, Any]:
        """Run the local test step.

        Args:
            repo_path: Local repository path where tests should run.
            task: Optional task text from the workflow. Used to decide
                whether tests should be skipped for simple non-code work.

        Returns:
            Structured result with success flag, summary, stdout, stderr,
            and the executed command.
        """
        # In mock mode, do not run real tests.
        if self.settings.enable_mock_tools:
            return {
                "success": True,
                "summary": "Mock test runner completed. No real tests were executed.",
                "command": "pytest -q",
                "stdout": "Mock test pass.",
                "stderr": "",
            }

        # Skip tests for simple non-code tasks.
        # Example: creating a markdown file or updating docs.
        if self._should_skip_tests(task):
            return {
                "success": True,
                "summary": "Test step skipped for a simple non-code task.",
                "command": "pytest -q",
                "stdout": "Skipped local tests.",
                "stderr": "",
            }

        # Read the test command from settings if it exists.
        # If not, use pytest as a safe default.
        command = getattr(self.settings, "test_command", "pytest -q")

        try:
            completed = subprocess.run(
                shlex.split(command),
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "summary": "Test execution timed out.",
                "command": command,
                "stdout": "",
                "stderr": "Timeout after 180 seconds.",
            }
        except Exception as exc:
            return {
                "success": False,
                "summary": f"Test execution failed with an exception: {exc}",
                "command": command,
                "stdout": "",
                "stderr": str(exc),
            }

        # Default rule: return code 0 means success.
        success = completed.returncode == 0
        stdout_text = (completed.stdout or "").lower()
        stderr_text = (completed.stderr or "").lower()

        # Small fix for repos or tasks where no tests exist yet.
        # This should not block simple demo tasks.
        if not success and "no tests ran" in stdout_text:
            success = True
            summary = "No tests were found. Accepted for this task."
        elif not success and "no tests collected" in stdout_text:
            success = True
            summary = "No tests were collected. Accepted for this task."
        elif success:
            summary = "Tests passed."
        else:
            summary = "Tests failed."

        return {
            "success": success,
            "summary": summary,
            "command": command,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def _should_skip_tests(self, task: str) -> bool:
        """Decide whether the test step should be skipped.

        This is a simple first version.
        Later, this logic can move to the Orchestrator or workflow state.
        """
        if not task:
            return False

        task_lower = task.lower()

        # Common non-code task signals.
        skip_keywords = [
            ".md",
            "markdown",
            "readme",
            "documentation",
            "docs",
            "create a file",
            "create file",
            "update doc",
            "write note",
        ]

        return any(keyword in task_lower for keyword in skip_keywords)