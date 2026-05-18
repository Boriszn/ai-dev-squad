"""Local model provider for AI Dev Squad.

This provider connects AI Dev Squad to a local model runtime through
Ollama. It keeps the same provider interface as Codex, so the graph
and agent flow do not need to change when switching between online
and offline providers.

Current behavior:
- Calls the local Ollama API
- Uses the configured local model from settings
- Uses the configured Ollama base URL from settings
- Returns structured output in the same general shape as other providers
- Includes model and token usage metadata when available

Important limitation:
This first version is generation-only.
It can produce implementation guidance or code text, but it does not
directly apply file changes to the local repository yet. A later step
can add a local file/tool execution layer on top of this provider.
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
    """Provider that sends coding tasks to a local Ollama model."""

    settings: Settings
    name: str = "local"

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

        # Build the messages for the local model call.
        # This first version tells the model the repo path and task,
        # but does not yet read and send real file contents.
        messages = self._build_messages(task=task, repo_path=repo_path)

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

        # This first version is intentionally honest.
        # It generates implementation output, but does not yet write files.
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

    def _build_messages(self, task: str, repo_path: str) -> list[dict[str, str]]:
        """Build chat messages for the local model call.

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

        Ollama responses usually expose:
        - prompt_eval_count
        - eval_count

        This method combines them into a simple total token count.

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