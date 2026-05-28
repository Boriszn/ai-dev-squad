"""Developer agent for AI Dev Squad.

The Developer Agent is responsible for sending coding requests to the
selected provider through the model router.

Why this agent exists:
- keeps provider execution out of the graph nodes
- keeps Codex and local-provider execution behind one interface
- normalizes provider output into a stable development result shape
- passes structured file-change data to the rest of the workflow
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.graph.state import WorkflowState
from app.models.model_router import ModelRouter


@dataclass
class DeveloperAgent:
    """Handle code change requests through the active model provider."""

    model_router: ModelRouter

    def execute(self, state: WorkflowState) -> dict[str, Any]:
        """Run the developer step.

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with normalized development results.
        """
        task = str(state.get("task", ""))
        repo_path = str(state.get("repo_path", "."))
        provider_name = str(
            state.get("provider_name") or self.model_router.default_provider_name
        ).strip().lower()

        raw_result = self.model_router.run_code_task(
            provider_name=provider_name,
            task=task,
            repo_path=repo_path,
        )

        development_result = self._normalize_result(
            result=raw_result,
            provider_name=provider_name,
            task=task,
            repo_path=repo_path,
        )

        new_messages = list(state.get("messages", []))
        new_messages.append(f"Developer Agent used provider: {provider_name}")
        new_messages.append(development_result["summary"])

        # Add provider notes to workflow messages when available.
        for note in development_result.get("notes", []):
            new_messages.append(note)

        success = bool(development_result["success"])
        current_step_index = max(int(state.get("current_step_index", 0) or 0), 1)

        step_results = list(state.get("step_results", []))
        step_results.append(
            {
                "step": "developer",
                "provider": provider_name,
                "success": success,
                "summary": development_result["summary"],
                "files_created": development_result["what_was_added"],
                "files_updated": development_result["files_changed"],
            }
        )

        return {
            "provider_name": provider_name,
            "development_result": development_result,
            "messages": new_messages,
            "status": "developed" if success else "development_failed",
            "current_step_index": current_step_index,
            "current_step": (
                "Developer step finished successfully"
                if success
                else "Developer step failed"
            ),
            "step_results": step_results,
        }

    def _normalize_result(
        self,
        result: dict[str, Any],
        provider_name: str,
        task: str,
        repo_path: str,
    ) -> dict[str, Any]:
        """Normalize provider output into a stable development result shape.

        Different providers can return slightly different payloads.
        This method makes sure the rest of the app always receives the
        same core fields.

        Args:
            result: Raw provider result.
            provider_name: Selected provider name.
            task: User task.
            repo_path: Target repository path.

        Returns:
            Normalized development result dictionary.
        """
        files_to_create = self._normalize_file_entries(result.get("files_to_create"))
        files_to_update = self._normalize_file_entries(result.get("files_to_update"))

        files_changed = self._normalize_string_list(
            result.get("files_changed"),
            fallback=[item["path"] for item in files_to_update],
        )
        what_was_added = self._normalize_string_list(
            result.get("what_was_added"),
            fallback=[item["path"] for item in files_to_create],
        )

        notes = self._normalize_string_list(result.get("notes"), fallback=[])

        normalized = {
            "success": bool(result.get("success")),
            "summary": str(result.get("summary", "No development summary available.")),
            "provider": str(result.get("provider", provider_name)),
            "task": str(result.get("task", task)),
            "repo_path": str(result.get("repo_path", repo_path)),
            "stdout": str(result.get("stdout", "")),
            "stderr": str(result.get("stderr", "")),
            "model_status": result.get("model_status", {}) or {},
            "files_to_create": files_to_create,
            "files_to_update": files_to_update,
            "files_changed": files_changed,
            "what_was_added": what_was_added,
            "notes": notes,
        }

        return normalized

    def _normalize_file_entries(self, value: Any) -> list[dict[str, str]]:
        """Normalize file entry objects.

        Expected shape:
        [
            {"path": "relative/path.py", "content": "..."}
        ]

        Args:
            value: Raw provider value.

        Returns:
            Clean normalized list of file entry dictionaries.
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

    def _normalize_string_list(
        self,
        value: Any,
        fallback: list[str],
    ) -> list[str]:
        """Normalize a list of strings with a fallback value.

        Args:
            value: Raw provider value.
            fallback: Fallback list if the value is missing or invalid.

        Returns:
            Clean string list.
        """
        if not isinstance(value, list):
            return fallback

        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned if cleaned else fallback