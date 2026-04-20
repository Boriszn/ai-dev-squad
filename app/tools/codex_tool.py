"""Codex CLI tool wrapper for AI Dev Squad.

This module contains the low-level wrapper that calls the local Codex CLI.
It is used by the Codex provider and keeps subprocess logic in one place.

Main behavior:
- Supports mock mode for safe early testing
- Verifies that the Codex CLI exists on PATH
- Runs Codex in non-interactive mode
- Prints simple progress messages to the console
- Returns a structured result for the LangGraph workflow
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from app.config.settings import Settings


@dataclass
class CodexTool:
    """Run a coding task through the local Codex CLI.

    This class is the execution layer for the Developer Agent when the
    selected provider is Codex.
    """

    settings: Settings

    def run(self, task: str, repo_path: str) -> dict[str, Any]:
        """Execute a coding task with Codex.

        Args:
            task: Natural language task that should be sent to Codex.
            repo_path: Local repository path where Codex should run.

        Returns:
            A structured dictionary with success flag, summary, stdout,
            stderr, provider name, task metadata, and model status.
        """
        command_name = self.settings.codex_cli_command

        # Default status object.
        # This keeps the return shape consistent in success and failure cases.
        status_info = {
            "tool": command_name,
            "provider": "codex",
            "execution_mode": "mock" if self.settings.enable_mock_tools else "real",
            "model": "unknown",
            "provider_backend": "unknown",
            "status": "not_started",
        }

        # In mock mode, do not call the real Codex CLI.
        if self.settings.enable_mock_tools:
            print(
                "[Developer Agent] Mock mode is enabled. "
                "Skipping real Codex execution.",
                flush=True,
            )
            status_info["status"] = "mocked"

            return {
                "success": True,
                "summary": (
                    "Mock Codex execution completed. "
                    "Disable ENABLE_MOCK_TOOLS to use the real Codex CLI."
                ),
                "provider": "codex",
                "task": task,
                "repo_path": repo_path,
                "stdout": "Mock mode: no command executed.",
                "stderr": "",
                "model_status": status_info,
            }

        print("[Developer Agent] Preparing Codex execution...", flush=True)
        print(f"[Developer Agent] Repo path: {repo_path}", flush=True)
        print(f"[Developer Agent] Task: {task}", flush=True)

        # Make sure the Codex CLI is available on the local machine.
        if shutil.which(command_name) is None:
            print(
                f"[Developer Agent] Codex CLI was not found on PATH: {command_name}",
                flush=True,
            )
            status_info["status"] = "failed"

            return {
                "success": False,
                "summary": f"Codex CLI command not found on PATH: {command_name}",
                "provider": "codex",
                "task": task,
                "repo_path": repo_path,
                "stdout": "",
                "stderr": "Missing Codex CLI.",
                "model_status": status_info,
            }

        # Build the real Codex command.
        # 'exec' runs Codex in non-interactive mode.
        # '--full-auto' allows Codex to perform the task automatically.
        command = [command_name, "exec", "--full-auto", task]

        print("[Developer Agent] Codex is running...", flush=True)

        try:
            completed = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )

            # Update status info with parsed model/backend details.
            parsed_status = self._extract_codex_status(completed.stderr)
            status_info.update(parsed_status)

        except subprocess.TimeoutExpired:
            print("[Developer Agent] Codex execution timed out.", flush=True)
            status_info["status"] = "timeout"

            return {
                "success": False,
                "summary": "Codex execution timed out.",
                "provider": "codex",
                "task": task,
                "repo_path": repo_path,
                "stdout": "",
                "stderr": "Timeout after 300 seconds.",
                "model_status": status_info,
            }

        except Exception as exc:
            print(
                f"[Developer Agent] Codex execution failed with exception: {exc}",
                flush=True,
            )
            status_info["status"] = "failed"

            return {
                "success": False,
                "summary": f"Codex execution failed with an exception: {exc}",
                "provider": "codex",
                "task": task,
                "repo_path": repo_path,
                "stdout": "",
                "stderr": str(exc),
                "model_status": status_info,
            }

        # Codex returns exit code 0 on success.
        success = completed.returncode == 0

        # Build a short summary for the workflow result.
        summary = (
            "Codex execution completed successfully."
            if success
            else "Codex execution finished with a non-zero exit code."
        )

        status_info["status"] = "completed" if success else "failed"

        print(
            "[Developer Agent] Codex finished. "
            f"Success: {success}. "
            f"Model: {status_info['model']}. "
            f"Backend: {status_info['provider_backend']}.",
            flush=True,
        )

        return {
            "success": success,
            "summary": summary,
            "provider": "codex",
            "task": task,
            "repo_path": repo_path,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "model_status": status_info,
        }

    def _extract_codex_status(self, stderr_text: str) -> dict[str, str]:
        """Extract simple status details from Codex CLI output.

        Codex prints useful execution details to stderr, including model
        name and backend provider.

        Args:
            stderr_text: Raw stderr text returned by Codex CLI.

        Returns:
            A dictionary with parsed model and provider backend details.
        """
        model = "unknown"
        provider_backend = "unknown"

        for line in stderr_text.splitlines():
            line = line.strip()
            if line.startswith("model:"):
                model = line.split("model:", 1)[1].strip()
            elif line.startswith("provider:"):
                provider_backend = line.split("provider:", 1)[1].strip()

        return {
            "model": model,
            "provider_backend": provider_backend,
        }