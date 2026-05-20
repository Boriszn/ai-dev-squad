"""Codex CLI tool wrapper for AI Dev Squad.

This module contains the low-level wrapper that calls the local Codex CLI.
It is used by the Codex provider and keeps subprocess logic in one place.

Main behavior:
- Supports mock mode for safe early testing
- Verifies that the Codex CLI exists on PATH
- Supports both Plan mode and Act mode
- Uses Codex non-interactive mode
- Uses structured schema output for planning
- Prints simple progress messages to the console
- Returns structured results for the LangGraph workflow
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config.settings import Settings


@dataclass
class CodexTool:
    """Run planning and coding tasks through the local Codex CLI.

    This class is the execution layer for the Developer Agent when the
    selected provider is Codex.
    """

    settings: Settings

    def plan_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Create a structured implementation plan with Codex.

        This method is used in Plan mode. It asks Codex to analyze the task
        and return a structured planning result before execution starts.

        Args:
            task: Natural language task from the user.
            repo_path: Local repository path related to the task.

        Returns:
            Structured planning result dictionary.
        """
        command_name = self.settings.codex_cli_command
        status_info = self._build_default_status(
            command_name=command_name,
            execution_mode="plan",
        )

        if self.settings.enable_mock_tools:
            print(
                "[Developer Agent] Mock mode is enabled. "
                "Skipping real Codex planning.",
                flush=True,
            )
            status_info["status"] = "mocked"

            mock_plan = self._build_mock_plan(task=task, repo_path=repo_path)
            mock_plan["model_status"] = status_info
            return mock_plan

        print("[Developer Agent] Preparing Codex planning step...", flush=True)
        print(f"[Developer Agent] Repo path: {repo_path}", flush=True)
        print(f"[Developer Agent] Task: {task}", flush=True)

        if shutil.which(command_name) is None:
            print(
                f"[Developer Agent] Codex CLI was not found on PATH: {command_name}",
                flush=True,
            )
            status_info["status"] = "failed"

            return self._build_plan_error_result(
                task=task,
                repo_path=repo_path,
                summary=f"Codex CLI command not found on PATH: {command_name}",
                stderr="Missing Codex CLI.",
                model_status=status_info,
            )

        planning_prompt = self._build_planning_prompt(task=task, repo_path=repo_path)
        planning_schema = self._build_planning_schema()

        schema_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                encoding="utf-8",
            ) as schema_file:
                json.dump(planning_schema, schema_file, indent=2)
                schema_path = schema_file.name

            command = [
                command_name,
                # --cd must be a top-level Codex flag so the selected repo is the
                # active workspace root instead of the AI Dev Squad app repo.
                "--cd",
                repo_path,
                "exec",
                "--output-schema",
                schema_path,
                planning_prompt,
            ]

            print("[Developer Agent] Codex planning is running...", flush=True)

            completed = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )

            parsed_status = self._extract_codex_status(completed.stderr)
            status_info.update(parsed_status)

        except subprocess.TimeoutExpired:
            print("[Developer Agent] Codex planning timed out.", flush=True)
            status_info["status"] = "timeout"

            return self._build_plan_error_result(
                task=task,
                repo_path=repo_path,
                summary="Codex planning timed out.",
                stderr="Timeout after 300 seconds.",
                model_status=status_info,
            )

        except Exception as exc:
            print(
                f"[Developer Agent] Codex planning failed with exception: {exc}",
                flush=True,
            )
            status_info["status"] = "failed"

            return self._build_plan_error_result(
                task=task,
                repo_path=repo_path,
                summary=f"Codex planning failed with an exception: {exc}",
                stderr=str(exc),
                model_status=status_info,
            )

        finally:
            if schema_path:
                try:
                    Path(schema_path).unlink(missing_ok=True)
                except Exception:
                    pass

        if completed.returncode != 0:
            status_info["status"] = "failed"
            return self._build_plan_error_result(
                task=task,
                repo_path=repo_path,
                summary="Codex planning finished with a non-zero exit code.",
                stderr=completed.stderr,
                model_status=status_info,
            )

        plan_result = self._parse_plan_output(
            stdout_text=completed.stdout,
            task=task,
            repo_path=repo_path,
        )

        status_info["status"] = "completed"
        plan_result["model_status"] = status_info

        print(
            "[Developer Agent] Codex planning finished successfully. "
            f"Model: {status_info['model']}. "
            f"Backend: {status_info['provider_backend']}.",
            flush=True,
        )

        return plan_result

    def run_code_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Execute a coding task with Codex.

        This method is used in Act mode after the user has already reviewed
        the plan and decided to continue.

        Args:
            task: Natural language task that should be sent to Codex.
            repo_path: Local repository path where Codex should run.

        Returns:
            A structured dictionary with success flag, summary, stdout,
            stderr, provider name, task metadata, and model status.
        """
        command_name = self.settings.codex_cli_command
        status_info = self._build_default_status(
            command_name=command_name,
            execution_mode="act",
        )

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

        # Use the current documented writable sandbox mode for Act.
        command = [
            command_name,
            # --cd sets the selected repo as Codex workspace root, and --add-dir
            # explicitly allows writes there under workspace-write sandbox mode.
            "--cd",
            repo_path,
            "--add-dir",
            repo_path,
            "exec",
            "--sandbox",
            "workspace-write",
            task,
        ]

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

        success = completed.returncode == 0
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

    def _build_default_status(
        self,
        command_name: str,
        execution_mode: str,
    ) -> dict[str, Any]:
        """Build the default model status object.

        Args:
            command_name: Codex CLI command name from settings.
            execution_mode: Current mode, for example plan or act.

        Returns:
            Default structured status dictionary.
        """
        return {
            "tool": command_name,
            "provider": "codex",
            "execution_mode": execution_mode,
            "model": "unknown",
            "provider_backend": "unknown",
            "status": "not_started",
            "tokens_used": None,
        }

    def _build_mock_plan(self, task: str, repo_path: str) -> dict[str, Any]:
        """Build a simple mock planning result.

        Args:
            task: User task.
            repo_path: Repository path.

        Returns:
            Structured mock planning result.
        """
        return {
            "success": True,
            "summary": "Mock Codex planning completed.",
            "provider": "codex",
            "task": task,
            "repo_path": repo_path,
            "plan_summary": f"Prepare an implementation plan for: {task}",
            "plan_steps": [
                "Review the task.",
                "Identify the likely files to update.",
                "Prepare implementation steps.",
                "Run tests after changes.",
            ],
            "planned_file_changes": {
                "create": [],
                "update": ["README.md"],
            },
            "plan_notes": [
                "This is mock planning output.",
            ],
            "act_summary": "Review the planned files and confirm execution.",
            "stdout": "",
            "stderr": "",
        }

    def _build_planning_prompt(self, task: str, repo_path: str) -> str:
        """Build the Codex planning prompt.

        Args:
            task: User task.
            repo_path: Repository path.

        Returns:
            Prompt text for Plan mode.
        """
        return (
            "You are planning a coding task for AI Dev Squad.\n\n"
            f"Repository path: {repo_path}\n"
            f"Task: {task}\n\n"
            "Return a structured implementation plan only.\n"
            "Do not apply changes.\n"
            "Do not run destructive actions.\n"
            "Think about what files will likely be created or updated.\n"
            "Keep the plan practical and short.\n"
        )

    def _build_planning_schema(self) -> dict[str, Any]:
        """Build the JSON schema for structured planning output.

        Returns:
            JSON schema dictionary used with Codex --output-schema.
        """
        return {
            "type": "object",
            "properties": {
                "plan_summary": {"type": "string"},
                "plan_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "planned_file_changes": {
                    "type": "object",
                    "properties": {
                        "create": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "update": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["create", "update"],
                    "additionalProperties": False,
                },
                "plan_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "act_summary": {"type": "string"},
            },
            "required": [
                "plan_summary",
                "plan_steps",
                "planned_file_changes",
                "plan_notes",
                "act_summary",
            ],
            "additionalProperties": False,
        }

    def _parse_plan_output(
        self,
        stdout_text: str,
        task: str,
        repo_path: str,
    ) -> dict[str, Any]:
        """Parse structured planning output from Codex stdout.

        Args:
            stdout_text: Final stdout text returned by Codex.
            task: User task.
            repo_path: Repository path.

        Returns:
            Structured planning result.
        """
        try:
            payload = json.loads(stdout_text)
        except json.JSONDecodeError:
            payload = {
                "plan_summary": "Codex returned non-JSON plan output.",
                "plan_steps": [
                    "Review the task.",
                    "Inspect the relevant files.",
                    "Prepare implementation changes.",
                    "Run tests after changes.",
                ],
                "planned_file_changes": {
                    "create": [],
                    "update": [],
                },
                "plan_notes": [
                    "Planning output could not be parsed as JSON cleanly.",
                ],
                "act_summary": "Review the plan before execution.",
            }

        return {
            "success": True,
            "summary": "Codex planning completed successfully.",
            "provider": "codex",
            "task": task,
            "repo_path": repo_path,
            "plan_summary": payload.get("plan_summary", ""),
            "plan_steps": payload.get("plan_steps", []),
            "planned_file_changes": payload.get(
                "planned_file_changes",
                {"create": [], "update": []},
            ),
            "plan_notes": payload.get("plan_notes", []),
            "act_summary": payload.get("act_summary", ""),
            "stdout": stdout_text,
            "stderr": "",
        }

    def _build_plan_error_result(
        self,
        task: str,
        repo_path: str,
        summary: str,
        stderr: str,
        model_status: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a consistent planning error result.

        Args:
            task: User task.
            repo_path: Repository path.
            summary: Short summary of the failure.
            stderr: Error text.
            model_status: Structured model status object.

        Returns:
            Structured planning error result.
        """
        return {
            "success": False,
            "summary": summary,
            "provider": "codex",
            "task": task,
            "repo_path": repo_path,
            "plan_summary": "Planning failed.",
            "plan_steps": [],
            "planned_file_changes": {
                "create": [],
                "update": [],
            },
            "plan_notes": [summary],
            "act_summary": "",
            "stdout": "",
            "stderr": stderr,
            "model_status": model_status,
        }

    def _extract_codex_status(self, stderr_text: str) -> dict[str, Any]:
        """Extract simple status details from Codex CLI output.

        Codex prints useful execution details to stderr, including model
        name, backend provider, and token usage.

        Args:
            stderr_text: Raw stderr text returned by Codex CLI.

        Returns:
            A dictionary with parsed model, provider backend, and token usage.
        """
        model = "unknown"
        provider_backend = "unknown"
        tokens_used: int | None = None

        token_patterns = [
            re.compile(r"tokens\s*used\s*:\s*([0-9][0-9,]*)", re.IGNORECASE),
            re.compile(r"token\s*usage\s*:\s*([0-9][0-9,]*)", re.IGNORECASE),
            re.compile(r"total\s*tokens\s*:\s*([0-9][0-9,]*)", re.IGNORECASE),
            re.compile(r"tokens\s+used\s+([0-9][0-9,]*)", re.IGNORECASE),
        ]

        for line in stderr_text.splitlines():
            line = line.strip()

            if line.startswith("model:"):
                model = line.split("model:", 1)[1].strip()
            elif line.startswith("provider:"):
                provider_backend = line.split("provider:", 1)[1].strip()

            if tokens_used is None:
                for pattern in token_patterns:
                    match = pattern.search(line)
                    if match:
                        parsed_value = match.group(1).replace(",", "")
                        try:
                            tokens_used = int(parsed_value)
                        except ValueError:
                            tokens_used = None
                        break

        return {
            "model": model,
            "provider_backend": provider_backend,
            "tokens_used": tokens_used,
        }