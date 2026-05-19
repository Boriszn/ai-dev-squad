"""Orchestrator agent for AI Dev Squad.

The Orchestrator is the control point of the workflow.
It receives the task, creates a structured plan, and evaluates whether the
workflow can continue or must wait for human approval.

Why this agent exists:
- keeps planning logic in one place
- keeps approval evaluation logic in one place
- makes the workflow easier to read and extend later
- prepares richer data for the Plan / Act UI flow

Current planning approach:
- first try provider-backed planning through the model router
- if provider planning fails, fall back to a safe local default plan
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.graph.state import WorkflowState
from app.models.model_router import ModelRouter


@dataclass
class OrchestratorAgent:
    """Plan and control the high-level workflow."""

    model_router: ModelRouter

    def create_plan(self, state: WorkflowState) -> dict[str, Any]:
        """Create a structured execution plan from the current task.

        This method prepares the planning data needed by the Plan / Act UI:
        - full plan text
        - short summary
        - numbered steps
        - file preview
        - notes / warnings
        - act summary

        Planning logic:
        1. validate task input
        2. choose the provider from workflow state
        3. ask the provider for a structured plan
        4. if provider planning fails, fall back to a safe default plan

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with the structured plan and
            initial approval-related information.
        """
        # Read and normalize core task settings from the current state.
        task = state.get("task", "").strip()
        provider_name = state.get("provider_name", "codex")
        repo_path = state.get("repo_path", ".")

        # Guard against an empty task.
        if not task:
            return {
                "plan": "No task provided.",
                "plan_summary": "No task provided.",
                "plan_steps": [],
                "planned_file_changes": {
                    "create": [],
                    "update": [],
                },
                "plan_notes": ["The task is empty."],
                "act_summary": "",
                "status": "failed",
                "phase": "plan",
                "approval_required": False,
                "error_message": "The task is empty.",
                "messages": state.get("messages", [])
                + ["Orchestrator could not create a plan because the task is empty."],
            }

        # Keep any existing approval status if one was already set.
        # Otherwise default to pending.
        approval_status = state.get("approval_status", "pending")
        messages = list(state.get("messages", []))

        # First try provider-backed planning.
        provider_plan = self._try_provider_plan(
            task=task,
            repo_path=repo_path,
            provider_name=provider_name,
        )

        if provider_plan["success"]:
            plan_steps = provider_plan["plan_steps"]
            plan = self._build_plain_plan_text(plan_steps)

            messages.append(
                f"Orchestrator created a provider-backed plan using: {provider_name}"
            )

            return {
                "plan": plan,
                "plan_summary": provider_plan["plan_summary"],
                "plan_steps": plan_steps,
                "planned_file_changes": provider_plan["planned_file_changes"],
                "plan_notes": provider_plan["plan_notes"],
                "act_summary": provider_plan["act_summary"],
                "phase": "plan",
                "status": "planned",
                "approval_status": approval_status,
                "approval_required": True,
                "provider_name": provider_name,
                "repo_path": repo_path,
                "total_steps": len(plan_steps),
                "current_step_index": 0,
                "current_step": "",
                "messages": messages,
            }

        # Fallback path:
        # if provider planning fails, create a safe local default plan so the
        # UI still works and the user is not blocked.
        fallback_plan = self._build_fallback_plan(task=task)

        messages.append(
            f"Provider-backed planning failed for {provider_name}. "
            "Used fallback plan instead."
        )
        messages.append(provider_plan["summary"])

        return {
            "plan": self._build_plain_plan_text(fallback_plan["plan_steps"]),
            "plan_summary": fallback_plan["plan_summary"],
            "plan_steps": fallback_plan["plan_steps"],
            "planned_file_changes": fallback_plan["planned_file_changes"],
            "plan_notes": fallback_plan["plan_notes"],
            "act_summary": fallback_plan["act_summary"],
            "phase": "plan",
            "status": "planned",
            "approval_status": approval_status,
            "approval_required": True,
            "provider_name": provider_name,
            "repo_path": repo_path,
            "total_steps": len(fallback_plan["plan_steps"]),
            "current_step_index": 0,
            "current_step": "",
            "messages": messages,
        }

    def check_approval(self, state: WorkflowState) -> dict[str, Any]:
        """Evaluate the current human approval state.

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update that says whether the workflow
            is approved, rejected, or still waiting.
        """
        approval_status = (state.get("approval_status") or "").lower().strip()
        messages = list(state.get("messages", []))

        if approval_status == "approved":
            messages.append("Approval granted. The workflow can continue.")
            return {
                "approval_status": "approved",
                "approval_required": False,
                "status": "approved",
                "messages": messages,
            }

        if approval_status == "rejected":
            messages.append("Approval rejected. The workflow will stop.")
            return {
                "approval_status": "rejected",
                "approval_required": False,
                "status": "rejected",
                "messages": messages,
            }

        messages.append("Approval not granted yet. Waiting for human decision.")
        return {
            "approval_status": "pending",
            "approval_required": True,
            "status": "waiting_for_approval",
            "messages": messages,
        }

    def _try_provider_plan(
        self,
        task: str,
        repo_path: str,
        provider_name: str,
    ) -> dict[str, Any]:
        """Try to create a plan through the selected provider.

        Args:
            task: User task text.
            repo_path: Repository path.
            provider_name: Selected provider name.

        Returns:
            A normalized planning result with a success flag.
        """
        try:
            result = self.model_router.plan_task(
                provider_name=provider_name,
                task=task,
                repo_path=repo_path,
            )
        except Exception as exc:
            return {
                "success": False,
                "summary": f"Provider planning failed with exception: {exc}",
                "plan_summary": "",
                "plan_steps": [],
                "planned_file_changes": {
                    "create": [],
                    "update": [],
                },
                "plan_notes": [],
                "act_summary": "",
            }

        # Normalize the result so the rest of the workflow has a stable shape.
        return {
            "success": bool(result.get("success")),
            "summary": str(result.get("summary", "")),
            "plan_summary": str(result.get("plan_summary", "")),
            "plan_steps": list(result.get("plan_steps", [])),
            "planned_file_changes": dict(
                result.get(
                    "planned_file_changes",
                    {
                        "create": [],
                        "update": [],
                    },
                )
            ),
            "plan_notes": list(result.get("plan_notes", [])),
            "act_summary": str(result.get("act_summary", "")),
        }

    def _build_fallback_plan(self, task: str) -> dict[str, Any]:
        """Build a safe fallback plan if provider planning fails.

        Args:
            task: User task text.

        Returns:
            A structured fallback planning object.
        """
        plan_steps = [
            "Review the task and understand the requested change.",
            "Inspect the relevant project files and current structure.",
            "Prepare the implementation approach and target file updates.",
            "Apply the code changes after approval.",
            "Run tests or validation checks.",
            "Return a final result summary.",
        ]

        task_lower = task.lower()

        if any(keyword in task_lower for keyword in ["readme", "docs", "documentation", ".md"]):
            plan_steps = [
                "Review the documentation task and current file structure.",
                "Identify the documentation files to update.",
                "Prepare the content changes after approval.",
                "Apply the documentation updates.",
                "Return a final result summary.",
            ]

        plan_notes = [
            "Human approval is required before development starts.",
            "Keep the change focused and avoid unrelated refactoring.",
            "This plan is a fallback because provider planning did not return a usable result.",
        ]

        if any(keyword in task_lower for keyword in ["delete", "remove", "drop"]):
            plan_notes.append("Check destructive actions carefully before execution.")

        if any(keyword in task_lower for keyword in ["test", "tests", "pytest"]):
            plan_notes.append("Expect validation or test execution as part of the flow.")

        return {
            "plan_summary": f"Prepare a safe implementation plan for: {task}",
            "plan_steps": plan_steps,
            "planned_file_changes": {
                "create": [],
                "update": [],
            },
            "plan_notes": plan_notes,
            "act_summary": (
                "Review the planned changes, check target files, and confirm "
                "before development starts."
            ),
        }

    def _build_plain_plan_text(self, plan_steps: list[str]) -> str:
        """Convert plan steps into the legacy plain-text plan field.

        Args:
            plan_steps: Ordered list of plan steps.

        Returns:
            One plain string containing the numbered plan.
        """
        return " ".join(
            f"{index + 1}. {step}" for index, step in enumerate(plan_steps)
        )