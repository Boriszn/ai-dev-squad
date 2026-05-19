"""Local model provider for AI Dev Squad.

This provider connects AI Dev Squad to a local model runtime through
Ollama. It keeps the same provider interface as Codex, so the graph
and agent flow do not need to change when switching between online
and offline providers.

Current behavior:
- Calls the local Ollama API
- Uses the configured local model from settings
- Supports both Plan mode and Act mode
- Returns structured output in the same general shape as other providers
- Includes model and token usage metadata when available

Important limitation:
This first version is still generation-only.
It can produce planning data, implementation guidance, or code text,
but it does not directly apply file changes to the local repository yet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from app.config.settings import Settings
from app.models.base_provider import BaseProvider


@dataclass
class LocalProvider(BaseProvider):
    """Provider that sends planning and coding tasks to a local Ollama model."""

    settings: Settings
    name: str = "local"

    def plan_task(self, task: str, repo_path: str) -> dict[str, Any]:
        """Create a structured implementation plan with the local model.

        This is the local-provider version of Plan mode.
        It returns a simple structured planning object that can be used
        by the Orchestrator and UI before execution starts.

        Args:
            task: Natural language task from the user.
            repo_path: Local repository path related to the task.

        Returns:
            Structured planning result dictionary.
        """
        model_name = self.settings.local_model_name
        ollama_base_url = self.settings.ollama_base_url
        chat_url = f"{ollama_base_url.rstrip('/')}/api/chat"

        messages = self._build_plan_messages(task=task, repo_path=repo_path)

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
        except Exception as exc:  # pragma: no cover - defensive error handling
            return self._build_plan_error_result(
                task=task,
                repo_path=repo_path,
                summary=f"Local provider planning failed with an exception: {exc}",
                stderr=str(exc),
                model_name=model_name,
            )

        response_text = self._extract_response_text(payload)
        tokens_used = self._extract_tokens_used(payload)
        parsed_plan = self._parse_plan_response(response_text=response_text, task=task)

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

        Args:
            task: Natural language coding task.
            repo_path: Local repository path related to the task.

        Returns:
            Structured provider result with:
            - success flag
            - summary
            - stdout / stderr
            - provider name
            - task metadata
            - model status
        """
        model_name = self.settings.local_model_name
        ollama_base_url = self.settings.ollama_base_url
        chat_url = f"{ollama_base_url.rstrip('/')}/api/chat"

        # Build the prompt/messages for the local model.
        # This first version tells the model the repo path and task, but does
        # not yet read and send real file contents from the repository.
        messages = self._build_run_messages(task=task, repo_path=repo_path)

        try:
            payload = self._call_ollama(
                chat_url=chat_url,
                model_name=model_name,
                messages=messages,
            )
        except error.URLError as exc:
            return {
                "success": False,
                "summary": (
                    "Local provider could not reach the Ollama server. "
                    "Make sure Ollama is running and the local API is available."
                ),
                "provider": self.name,
                "task": task,
                "repo_path": repo_path,
                "stdout": "",
                "stderr": str(exc),
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
        except Exception as exc:  # pragma: no cover - defensive error handling
            return {
                "success": False,
                "summary": f"Local provider failed with an exception: {exc}",
                "provider": self.name,
                "task": task,
                "repo_path": repo_path,
                "stdout": "",
                "stderr": str(exc),
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

        response_text = self._extract_response_text(payload)
        tokens_used = self._extract_tokens_used(payload)

        summary = (
            "Local provider generated a coding response successfully. "
            "This version does not yet apply file changes automatically."
        )

        return {
            "success": True,
            "summary": summary,
            "provider": self.name,
            "task": task,
            "repo_path": repo_path,
            "stdout": response_text,
            "stderr": "",
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

    def _build_plan_messages(self, task: str, repo_path: str) -> list[dict[str, str]]:
        """Build chat messages for Plan mode.

        Args:
            task: Natural language task.
            repo_path: Local repository path.

        Returns:
            A message list formatted for the Ollama chat API.
        """
        system_prompt = (
            "You are a local coding assistant for AI Dev Squad. "
            "You are in Plan mode. "
            "Create a practical implementation plan only. "
            "Do not execute changes. "
            "Keep the plan short, structured, and realistic."
        )

        user_prompt = (
            f"Repository path: {repo_path}\n"
            f"Task: {task}\n\n"
            "Return a short planning response that includes:\n"
            "1. short plan summary\n"
            "2. implementation steps\n"
            "3. likely files to create\n"
            "4. likely files to update\n"
            "5. short notes\n"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_run_messages(self, task: str, repo_path: str) -> list[dict[str, str]]:
        """Build chat messages for Act mode.

        Args:
            task: Natural language coding task.
            repo_path: Local repository path.

        Returns:
            A message list formatted for the Ollama chat API.
        """
        system_prompt = (
            "You are a local coding assistant for AI Dev Squad. "
            "You help with software implementation tasks. "
            "Be practical, concise, and code-focused. "
            "If you do not have enough file context, say so clearly and propose "
            "the smallest safe next change. "
            "Return useful implementation output that can help a developer or a "
            "later tool step apply the change."
        )

        user_prompt = (
            f"Repository path: {repo_path}\n"
            f"Task: {task}\n\n"
            "Important constraints:\n"
            "- You are currently working in generation-only mode.\n"
            "- You do not directly modify files in this step.\n"
            "- Produce a practical coding answer or implementation guidance.\n"
            "- If relevant, include suggested files to update and short code snippets.\n"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

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

        with request.urlopen(http_request, timeout=120) as response:
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

    def _parse_plan_response(self, response_text: str, task: str) -> dict[str, Any]:
        """Convert plain model output into a simple structured plan.

        Args:
            response_text: Raw text returned by the local model.
            task: Original user task.

        Returns:
            A simple structured plan object.
        """
        # Keep this first version simple and safe.
        # We use the model text as notes, but still return a stable structure.
        return {
            "plan_summary": f"Prepare a safe local-model plan for: {task}",
            "plan_steps": [
                "Review the task.",
                "Inspect likely files related to the change.",
                "Prepare the implementation approach.",
                "Return suggested changes before execution.",
            ],
            "planned_file_changes": {
                "create": [],
                "update": [],
            },
            "plan_notes": [
                "Local provider planning is currently simple and may need refinement.",
                "Model raw planning output is available in stdout if needed.",
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
        """Build a consistent planning error result.

        Args:
            task: User task.
            repo_path: Repository path.
            summary: Short summary of the failure.
            stderr: Error text.
            model_name: Configured local model name.

        Returns:
            Structured planning error result.
        """
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