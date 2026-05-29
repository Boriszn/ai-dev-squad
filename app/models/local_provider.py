"""Local model provider for AI Dev Squad.

This provider connects AI Dev Squad to a local model runtime through
Ollama. It keeps the same provider interface as Codex, so the graph
and agent flow do not need to change when switching between online
and offline providers.

Current behavior:
- Calls the local Ollama API
- Uses the configured local model from settings
- Supports both Plan mode and Act mode
- Reads a safe subset of repository files to build repo-aware context
- Returns structured planning/execution output
- Includes model and token usage metadata when available

Important limitation:
This version is repo-aware, but execution is still generation-only.
It can analyze the repository and return structured file changes,
but it does not apply file writes yet.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

from app.config.settings import Settings
from app.models.base_provider import BaseProvider


@dataclass
class LocalProvider(BaseProvider):
    """Provider that sends planning and coding tasks to a local Ollama model."""

    settings: Settings
    name: str = "local"

    # -------------------------------------------------------------------------
    # Public provider interface
    # -------------------------------------------------------------------------

    def plan_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Create a structured implementation plan with the local model.

        This Plan mode implementation is repo-aware. It reads a safe subset
        of files from the repository, builds context, and asks the local
        model for a structured plan.

        Args:
            task: Natural language task from the user.
            repo_path: Local repository path related to the task.

        Returns:
            Structured planning result dictionary.
        """
        model_name = self.settings.local_model_name
        ollama_base_url = self.settings.ollama_base_url
        chat_url = f"{ollama_base_url.rstrip('/')}/api/chat"

        repo_context = self._build_repo_context(repo_path=repo_path)
        messages = self._build_plan_messages(
            task=task,
            repo_context=repo_context,
        )

        try:
            payload = self._call_ollama(
                chat_url=chat_url,
                model_name=model_name,
                messages=messages,
            )
        except error.URLError as exc:
            return self._build_plan_error_result(
                task=task,
                repo_path=repo_path,
                summary=(
                    "Local provider could not reach the Ollama server. "
                    "Make sure Ollama is running and the local API is available."
                ),
                stderr=str(exc),
                model_name=model_name,
            )
        except Exception as exc:  # pragma: no cover - defensive handling
            return self._build_plan_error_result(
                task=task,
                repo_path=repo_path,
                summary=f"Local provider planning failed with an exception: {exc}",
                stderr=str(exc),
                model_name=model_name,
            )

        response_text = self._extract_response_text(payload)
        tokens_used = self._extract_tokens_used(payload)
        parsed_plan = self._parse_plan_response(
            response_text=response_text,
            task=task,
        )

        return {
            "success": True,
            "summary": "Local provider planning completed successfully.",
            "provider": self.name,
            "task": task,
            "repo_path": repo_path,
            "plan_summary": parsed_plan["plan_summary"],
            "plan_steps": parsed_plan["plan_steps"],
            "planned_file_changes": parsed_plan["planned_file_changes"],
            "plan_notes": parsed_plan["plan_notes"],
            "act_summary": parsed_plan["act_summary"],
            "stdout": response_text,
            "stderr": "",
            "model_status": {
                "tool": "ollama",
                "provider": self.name,
                "execution_mode": "plan",
                "model": model_name,
                "provider_backend": "ollama",
                "status": "completed",
                "tokens_used": tokens_used,
            },
        }

    def run_code_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Run a coding task with a local Ollama-backed model.

        This Act mode implementation is repo-aware. It reads a safe subset
        of repository files, asks the model for structured file changes, and
        returns the model output. File writes are not applied yet in this
        version.

        Args:
            task: Natural language coding task.
            repo_path: Local repository path related to the task.

        Returns:
            Structured provider result dictionary.
        """
        model_name = self.settings.local_model_name
        ollama_base_url = self.settings.ollama_base_url
        chat_url = f"{ollama_base_url.rstrip('/')}/api/chat"

        repo_context = self._build_repo_context(repo_path=repo_path)
        messages = self._build_run_messages(
            task=task,
            repo_context=repo_context,
        )

        try:
            payload = self._call_ollama(
                chat_url=chat_url,
                model_name=model_name,
                messages=messages,
            )
        except error.URLError as exc:
            return self._build_run_error_result(
                task=task,
                repo_path=repo_path,
                summary=(
                    "Local provider could not reach the Ollama server. "
                    "Make sure Ollama is running and the local API is available."
                ),
                stderr=str(exc),
                model_name=model_name,
            )
        except Exception as exc:  # pragma: no cover - defensive handling
            return self._build_run_error_result(
                task=task,
                repo_path=repo_path,
                summary=f"Local provider execution failed with an exception: {exc}",
                stderr=str(exc),
                model_name=model_name,
            )

        response_text = self._extract_response_text(payload)
        tokens_used = self._extract_tokens_used(payload)
        parsed_run = self._parse_run_response(
            response_text=response_text,
            task=task,
        )

        files_to_create = parsed_run["files_to_create"]
        files_to_update = parsed_run["files_to_update"]

        return {
            "success": True,
            "summary": parsed_run["summary"],
            "provider": self.name,
            "task": task,
            "repo_path": repo_path,
            "stdout": response_text,
            "stderr": "",
            "files_to_create": files_to_create,
            "files_to_update": files_to_update,
            "files_changed": [item["path"] for item in files_to_update],
            "what_was_added": [item["path"] for item in files_to_create],
            "notes": parsed_run["notes"],
            "model_status": {
                "tool": "ollama",
                "provider": self.name,
                "execution_mode": "generation_only",
                "model": model_name,
                "provider_backend": "ollama",
                "status": "completed",
                "tokens_used": tokens_used,
            },
        }

    # -------------------------------------------------------------------------
    # Repo context helpers
    # -------------------------------------------------------------------------

    def _build_repo_context(self, repo_path: str) -> dict[str, Any]:
        """Build a safe repository context snapshot.

        This keeps the prompt size under control by:
        - scanning only a limited number of files
        - reading only text-like files
        - truncating file contents
        - skipping noisy/generated folders

        Args:
            repo_path: Target repository path.

        Returns:
            A dictionary containing file list and sampled file contents.
        """
        root = Path(repo_path).expanduser().resolve()

        if not root.exists():
            return {
                "repo_path": str(root),
                "exists": False,
                "files": [],
                "files_text": "Repository path does not exist.",
            }

        if not root.is_dir():
            return {
                "repo_path": str(root),
                "exists": False,
                "files": [],
                "files_text": "Repository path is not a directory.",
            }

        collected_files: list[Path] = []
        ignored_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".mypy_cache",
            ".ruff_cache",
            ".idea",
            ".vscode",
            "dist",
            "build",
        }

        for path in root.rglob("*"):
            if len(collected_files) >= 40:
                break

            if not path.is_file():
                continue

            if any(part in ignored_dirs for part in path.parts):
                continue

            if not self._is_supported_text_file(path):
                continue

            collected_files.append(path)

        relative_file_names = [str(path.relative_to(root)) for path in collected_files]

        file_sections: list[str] = []
        for path in collected_files[:20]:
            relative_path = str(path.relative_to(root))
            content = self._read_text_file(path)
            if not content:
                continue

            file_sections.append(
                f"FILE: {relative_path}\n"
                "-----\n"
                f"{content}\n"
            )

        files_text = "\n\n".join(file_sections)
        if not files_text:
            files_text = "No readable text files were collected."

        return {
            "repo_path": str(root),
            "exists": True,
            "files": relative_file_names,
            "files_text": files_text,
        }

    def _is_supported_text_file(self, path: Path) -> bool:
        """Check whether a file should be included in repo context.

        Args:
            path: File path.

        Returns:
            True if the file looks like a text/source/config file.
        """
        supported_suffixes = {
            ".py",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".env",
            ".gitignore",
            ".sh",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".html",
            ".css",
            ".sql",
            ".xml",
        }

        return path.suffix.lower() in supported_suffixes or path.name in {
            "Dockerfile",
            "Makefile",
            "README",
            "README.md",
            ".gitignore",
        }

    def _read_text_file(self, path: Path) -> str:
        """Read and truncate a text file safely.

        Args:
            path: File path to read.

        Returns:
            Truncated text content, or an empty string if unreadable.
        """
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

        content = content.strip()
        if not content:
            return ""

        return content[:8000]

    # -------------------------------------------------------------------------
    # Prompt builders
    # -------------------------------------------------------------------------

    def _build_plan_messages(
        self,
        task: str,
        repo_context: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Build chat messages for Plan mode.

        Args:
            task: Natural language task.
            repo_context: Safe repository context snapshot.

        Returns:
            A message list formatted for the Ollama chat API.
        """
        system_prompt = (
            "You are a local coding assistant for AI Dev Squad. "
            "You are in Plan mode. "
            "Analyze the repository context carefully and create a practical implementation plan. "
            "If the task includes a previous accepted plan and new refinements, preserve earlier decisions unless the new refinement explicitly changes them. "
            "Do not restart the plan from scratch. "
            "Do not execute changes. "
            "Do not repeat the full user prompt in the summary. "
            "Do not wrap the answer in markdown fences. "
            "Return only valid JSON."
        )

        user_prompt = (
            f"Repository path: {repo_context['repo_path']}\n"
            f"Task: {task}\n\n"
            "Repository files:\n"
            f"{self._format_file_list(repo_context['files'])}\n\n"
            "Repository file contents snapshot:\n"
            f"{repo_context['files_text']}\n\n"
            "Return ONLY valid JSON with this shape:\n"
            "{\n"
            '  "plan_summary": "short summary without repeating the full task text",\n'
            '  "plan_steps": ["step 1", "step 2"],\n'
            '  "planned_file_changes": {\n'
            '    "create": ["path/to/file"],\n'
            '    "update": ["path/to/file"]\n'
            "  },\n"
            '  "plan_notes": ["note 1"],\n'
            '  "act_summary": "short next-step summary"\n'
            "}\n\n"
            "Rules:\n"
            "- If you are not confident about file predictions, return empty arrays.\n"
            "- Keep plan_summary short.\n"
            "- Do not echo the full prompt.\n"
            "- Preserve previous accepted decisions unless the newest refinement overrides them.\n"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_run_messages(
        self,
        task: str,
        repo_context: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Build chat messages for Act mode.

        Args:
            task: Natural language coding task.
            repo_context: Safe repository context snapshot.

        Returns:
            A message list formatted for the Ollama chat API.
        """
        system_prompt = (
            "You are a local coding assistant for AI Dev Squad. "
            "You are in Act mode, but file writes are still handled outside the model. "
            "Analyze the repository context and return structured file changes only. "
            "If the task includes a previous accepted plan and new refinements, preserve earlier accepted decisions unless the newest refinement explicitly changes them. "
            "Do not restart from scratch. "
            "Do not return shell commands. "
            "Do not return markdown fences. "
            "Do not return explanations outside JSON. "
            "Return only valid JSON."
        )

        user_prompt = (
            f"Repository path: {repo_context['repo_path']}\n"
            f"Task: {task}\n\n"
            "Repository files:\n"
            f"{self._format_file_list(repo_context['files'])}\n\n"
            "Repository file contents snapshot:\n"
            f"{repo_context['files_text']}\n\n"
            "Return ONLY valid JSON with this shape:\n"
            "{\n"
            '  "summary": "short execution summary",\n'
            '  "files_to_create": [\n'
            '    {"path": "path/to/file", "content": "full file content"}\n'
            "  ],\n"
            '  "files_to_update": [\n'
            '    {"path": "path/to/file", "content": "full updated file content"}\n'
            "  ],\n"
            '  "notes": ["note 1"]\n'
            "}\n\n"
            "Rules:\n"
            "- Only include files you are confident about.\n"
            "- If uncertain, return empty file arrays.\n"
            "- Keep summary short.\n"
            "- Preserve previous accepted decisions unless the newest refinement overrides them.\n"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _format_file_list(self, files: list[str]) -> str:
        """Format repository file list for prompts.

        Args:
            files: Relative file paths.

        Returns:
            Newline-separated file list.
        """
        if not files:
            return "(no files found)"
        return "\n".join(f"- {item}" for item in files)

    # -------------------------------------------------------------------------
    # Ollama call helpers
    # -------------------------------------------------------------------------

    def _call_ollama(
        self,
        chat_url: str,
        model_name: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Call the local Ollama chat API.

        Args:
            chat_url: Full Ollama chat endpoint URL.
            model_name: Local model name, for example qwen2.5-coder:7b.
            messages: Message list for the chat call.

        Returns:
            Parsed JSON payload from Ollama.

        Raises:
            urllib.error.URLError: If the local Ollama server cannot be reached.
            RuntimeError: If the response is empty or invalid.
        """
        request_payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
        }

        request_bytes = json.dumps(request_payload).encode("utf-8")
        http_request = request.Request(
            chat_url,
            data=request_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with request.urlopen(http_request, timeout=180) as response:
            response_body = response.read().decode("utf-8")

        if not response_body:
            raise RuntimeError("Ollama returned an empty response body.")

        return json.loads(response_body)

    def _extract_response_text(self, payload: dict[str, Any]) -> str:
        """Extract assistant text from the Ollama response payload.

        Args:
            payload: Parsed JSON response from Ollama.

        Returns:
            Assistant response text, or an empty string if missing.
        """
        message = payload.get("message", {})
        content = message.get("content", "")

        if isinstance(content, str):
            return content

        return ""

    def _extract_tokens_used(self, payload: dict[str, Any]) -> int | None:
        """Extract total token usage from the Ollama response if available.

        Args:
            payload: Parsed JSON response from Ollama.

        Returns:
            Total token count if both values are available, otherwise None.
        """
        prompt_eval_count = payload.get("prompt_eval_count")
        eval_count = payload.get("eval_count")

        if isinstance(prompt_eval_count, int) and isinstance(eval_count, int):
            return prompt_eval_count + eval_count

        return None

    # -------------------------------------------------------------------------
    # Response parsing
    # -------------------------------------------------------------------------

    def _parse_plan_response(
        self,
        response_text: str,
        task: str,
    ) -> dict[str, Any]:
        """Parse structured planning output from the local model.

        Args:
            response_text: Raw model response.
            task: Original user task.

        Returns:
            Structured plan object.
        """
        payload = self._extract_json_payload(response_text)

        if payload is None:
            return self._build_fallback_plan()

        plan_steps = self._safe_string_list(payload.get("plan_steps"))
        if not plan_steps:
            plan_steps = [
                "Review the task.",
                "Inspect the repository structure and relevant files.",
                "Prepare the implementation approach.",
                "Return suggested changes before execution.",
            ]

        return {
            "plan_summary": self._normalize_plan_summary(
                value=payload.get("plan_summary"),
                task=task,
            ),
            "plan_steps": plan_steps,
            "planned_file_changes": self._safe_file_change_map(
                payload.get("planned_file_changes")
            ),
            "plan_notes": self._safe_string_list(payload.get("plan_notes")),
            "act_summary": self._normalize_short_text(
                value=payload.get("act_summary"),
                fallback="Review the plan and confirm before execution starts.",
                max_length=160,
            ),
        }

    def _parse_run_response(
        self,
        response_text: str,
        task: str,
    ) -> dict[str, Any]:
        """Parse structured execution output from the local model.

        Args:
            response_text: Raw model response.
            task: Original user task.

        Returns:
            Structured execution object.
        """
        payload = self._extract_json_payload(response_text)

        if payload is None:
            return {
                "summary": f"Local model returned non-JSON execution output for: {task}",
                "files_to_create": [],
                "files_to_update": [],
                "notes": [
                    "Execution output could not be parsed as JSON.",
                    "Raw model output is available in stdout.",
                ],
            }

        return {
            "summary": self._normalize_short_text(
                value=payload.get("summary"),
                fallback="Local model produced an execution plan.",
                max_length=200,
            ),
            "files_to_create": self._safe_file_entries(payload.get("files_to_create")),
            "files_to_update": self._safe_file_entries(payload.get("files_to_update")),
            "notes": self._safe_string_list(payload.get("notes")),
        }

    def _extract_json_payload(self, response_text: str) -> dict[str, Any] | None:
        """Extract a JSON object from model output.

        Supports:
        - raw JSON object
        - fenced ```json blocks
        - fallback first {...} block extraction

        Args:
            response_text: Raw model output text.

        Returns:
            Parsed JSON dict, or None if parsing fails.
        """
        text = response_text.strip()
        if not text:
            return None

        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(
            r"```json\s*(\{.*?\})\s*```",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if fenced_match:
            try:
                payload = json.loads(fenced_match.group(1))
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass

        object_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if object_match:
            try:
                payload = json.loads(object_match.group(1))
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass

        return None

    def _safe_string_list(self, value: Any) -> list[str]:
        """Convert a value into a clean list of strings."""
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _safe_file_change_map(self, value: Any) -> dict[str, list[str]]:
        """Normalize planned file change map.

        If the model is not confident, or if parsing fails, we prefer empty
        arrays instead of misleading fallback guesses.
        """
        if not isinstance(value, dict):
            return {"create": [], "update": []}

        return {
            "create": self._safe_string_list(value.get("create")),
            "update": self._safe_string_list(value.get("update")),
        }

    def _safe_file_entries(self, value: Any) -> list[dict[str, str]]:
        """Normalize file-create/file-update entries.

        Expected input shape:
        [
            {"path": "path/to/file", "content": "full file content"}
        ]
        """
        if not isinstance(value, list):
            return []

        normalized: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue

            path = str(item.get("path", "")).strip()
            content = str(item.get("content", ""))

            if not path:
                continue

            normalized.append(
                {
                    "path": path,
                    "content": content,
                }
            )

        return normalized

    def _normalize_plan_summary(self, value: Any, task: str) -> str:
        """Normalize the plan summary and reduce prompt echo.

        Args:
            value: Raw model value.
            task: Original user task.

        Returns:
            Short normalized summary.
        """
        summary = str(value or "").strip()
        task_compact = " ".join(task.split()).strip()

        if not summary:
            return "Review the repository and prepare the requested change."

        if summary.startswith("Prepare a safe local-model plan for:"):
            return "Review the repository and prepare the requested change."

        if task_compact and task_compact[:80] in summary and len(summary) > 120:
            return "Review the repository and prepare the requested change."

        return self._truncate_single_line(summary, max_length=160)

    def _normalize_short_text(
        self,
        value: Any,
        fallback: str,
        max_length: int,
    ) -> str:
        """Normalize short text fields."""
        text = str(value or "").strip()
        if not text:
            return fallback
        return self._truncate_single_line(text, max_length=max_length)

    def _truncate_single_line(self, text: str, max_length: int) -> str:
        """Collapse whitespace and truncate a short summary line."""
        compact = " ".join(text.split())
        if len(compact) <= max_length:
            return compact
        return compact[: max_length - 3].rstrip() + "..."

    # -------------------------------------------------------------------------
    # Fallbacks and error helpers
    # -------------------------------------------------------------------------

    def _build_fallback_plan(self) -> dict[str, Any]:
        """Build a safe fallback plan if JSON parsing fails.

        Important:
        We return empty file predictions here instead of guessed file names.
        That keeps the UI honest when model planning output is not reliable.
        """
        return {
            "plan_summary": "Review the repository and prepare the requested change.",
            "plan_steps": [
                "Review the task.",
                "Inspect the repository structure and relevant files.",
                "Prepare the implementation approach.",
                "Return suggested changes before execution.",
            ],
            "planned_file_changes": {
                "create": [],
                "update": [],
            },
            "plan_notes": [
                "Local provider planning is currently simple and may need refinement.",
                "Model output could not be parsed as JSON cleanly.",
            ],
            "act_summary": "Review the plan and confirm before execution starts.",
        }

    def _build_plan_error_result(
        self,
        task: str,
        repo_path: str,
        summary: str,
        stderr: str,
        model_name: str,
    ) -> dict[str, Any]:
        """Build a consistent planning error result."""
        return {
            "success": False,
            "summary": summary,
            "provider": self.name,
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
            "model_status": {
                "tool": "ollama",
                "provider": self.name,
                "execution_mode": "plan",
                "model": model_name,
                "provider_backend": "ollama",
                "status": "failed",
                "tokens_used": None,
            },
        }

    def _build_run_error_result(
        self,
        task: str,
        repo_path: str,
        summary: str,
        stderr: str,
        model_name: str,
    ) -> dict[str, Any]:
        """Build a consistent execution error result."""
        return {
            "success": False,
            "summary": summary,
            "provider": self.name,
            "task": task,
            "repo_path": repo_path,
            "stdout": "",
            "stderr": stderr,
            "files_to_create": [],
            "files_to_update": [],
            "files_changed": [],
            "what_was_added": [],
            "notes": [summary],
            "model_status": {
                "tool": "ollama",
                "provider": self.name,
                "execution_mode": "generation_only",
                "model": model_name,
                "provider_backend": "ollama",
                "status": "failed",
                "tokens_used": None,
            },
        }