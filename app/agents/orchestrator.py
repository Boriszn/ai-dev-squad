"""Orchestrator agent for AI Dev Squad.

The Orchestrator is the control point of the workflow.
It receives the task, creates a structured plan, and evaluates whether the
workflow can continue or must wait for human approval.

Why this agent exists:
- keeps planning logic in one place
- keeps approval evaluation logic in one place
- makes the workflow easier to read and extend later
- prepares richer data for the Plan / Act UI flow
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.graph.state import WorkflowState


@dataclass
class OrchestratorAgent:
    """Plan and control the high-level workflow."""

    def create_plan(self, state: WorkflowState) -> dict[str, Any]:
        """Create a structured execution plan from the current task.

        This method prepares the planning data needed by the Plan / Act UI:
        - full plan text
        - short summary
        - numbered steps
        - notes/warnings
        - simple act summary

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with the structured plan and
            initial approval-related information.
        """
        # Read and normalize the task text.
        task = state.get("task", "").strip()

        # Guard against an empty task.
        if not task:
            return {
                "plan": "No task provided.",
                "plan_summary": "No task provided.",
                "plan_steps": [],
                "plan_notes": ["The task is empty."],
                "act_summary": "",
                "status": "failed",
                "phase": "plan",
                "approval_required": False,
                "error_message": "The task is empty.",
                "messages": state.get("messages", [])
                + ["Orchestrator could not create a plan because the task is empty."],
            }

        # Build a simple structured plan.
        # This is intentionally lightweight for now. Later we can make
        # it more dynamic and task-aware.
        plan_summary = self._build_plan_summary(task)
        plan_steps = self._build_plan_steps(task)
        plan_notes = self._build_plan_notes(task)

        # Keep the legacy plain-text plan too, because other parts of the app
        # still display it.
        plan = " ".join(f"{index + 1}. {step}" for index, step in enumerate(plan_steps))

        # Short summary used later for the Act preview card.
        act_summary = (
            "Review the planned changes, check target files, and confirm "
            "before development starts."
        )

        # Keep any existing approval status if one was already set.
        # Otherwise default to pending.
        approval_status = state.get("approval_status", "pending")

        messages = list(state.get("messages", []))
        messages.append(f"Orchestrator created a plan for task: {task}")

        return {
            "plan": plan,
            "plan_summary": plan_summary,
            "plan_steps": plan_steps,
            "plan_notes": plan_notes,
            "act_summary": act_summary,
            "phase": "plan",
            "status": "planned",
            "approval_status": approval_status,
            "approval_required": True,
            "total_steps": len(plan_steps),
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
        # Normalize the approval value from state.
        approval_status = (state.get("approval_status") or "").lower().strip()
        messages = list(state.get("messages", []))

        # Approved path: workflow can continue to development.
        if approval_status == "approved":
            messages.append("Approval granted. The workflow can continue.")
            return {
                "approval_status": "approved",
                "approval_required": False,
                "status": "approved",
                "messages": messages,
            }

        # Rejected path: workflow should stop cleanly.
        if approval_status == "rejected":
            messages.append("Approval rejected. The workflow will stop.")
            return {
                "approval_status": "rejected",
                "approval_required": False,
                "status": "rejected",
                "messages": messages,
            }

        # Default path: still waiting for a human decision.
        messages.append("Approval not granted yet. Waiting for human decision.")
        return {
            "approval_status": "pending",
            "approval_required": True,
            "status": "waiting_for_approval",
            "messages": messages,
        }

    def _build_plan_summary(self, task: str) -> str:
        """Build a short summary line for the Plan card.

        Args:
            task: User task text.

        Returns:
            Short plan summary text.
        """
        return f"Prepare a safe implementation plan for: {task}"

    def _build_plan_steps(self, task: str) -> list[str]:
        """Build a simple numbered implementation plan.

        Args:
            task: User task text.

        Returns:
            A list of ordered plan steps.
        """
        # Start with a safe default flow that fits most coding tasks.
        steps = [
            "Review the task and understand the requested change.",
            "Inspect the relevant project files and current structure.",
            "Prepare the implementation approach and target file updates.",
            "Apply the code changes after approval.",
            "Run tests or validation checks.",
            "Return a final result summary.",
        ]

        # Keep the first version simple, but slightly adapt docs-only tasks.
        task_lower = task.lower()
        if any(keyword in task_lower for keyword in ["readme", "docs", "documentation", ".md"]):
            steps = [
                "Review the documentation task and current file structure.",
                "Identify the documentation files to update.",
                "Prepare the content changes after approval.",
                "Apply the documentation updates.",
                "Return a final result summary.",
            ]

        return steps

    def _build_plan_notes(self, task: str) -> list[str]:
        """Build optional notes or warnings for the Plan card.

        Args:
            task: User task text.

        Returns:
            A list of short plan notes.
        """
        notes = [
            "Human approval is required before development starts.",
            "Keep the change focused and avoid unrelated refactoring.",
        ]

        task_lower = task.lower()

        if any(keyword in task_lower for keyword in ["delete", "remove", "drop"]):
            notes.append("Check destructive actions carefully before execution.")

        if any(keyword in task_lower for keyword in ["test", "tests", "pytest"]):
            notes.append("Expect validation or test execution as part of the flow.")

        return notes