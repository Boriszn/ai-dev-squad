"""Orchestrator agent for AI Dev Squad.

The Orchestrator is the control point of the workflow.
It receives the task, creates a simple plan, and evaluates whether the
workflow can continue or must wait for human approval.

Why this agent exists:
- keeps planning logic in one place
- keeps approval evaluation logic in one place
- makes the workflow easier to read and extend later
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.graph.state import WorkflowState


@dataclass
class OrchestratorAgent:
    """Plan and control the high-level workflow."""

    def create_plan(self, state: WorkflowState) -> dict[str, Any]:
        """Create a simple execution plan from the current task.

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with the execution plan and
            initial approval-related information.
        """
        # Read and normalize the task text.
        task = state.get("task", "").strip()

        # Guard against an empty task.
        if not task:
            return {
                "plan": "No task provided.",
                "status": "failed",
                "approval_required": False,
                "error_message": "The task is empty.",
                "messages": state.get("messages", [])
                + ["Orchestrator could not create a plan because the task is empty."],
            }

        # Create a simple first version of the workflow plan.
        # This can later become more dynamic and task-aware.
        plan = (
            "1. Review the task. "
            "2. Ask for approval before changes. "
            "3. Send approved task to the Developer Agent. "
            "4. Run the Tester Agent. "
            "5. Return the result."
        )

        # Keep any existing approval status if one was already set.
        # Otherwise default to pending.
        approval_status = state.get("approval_status", "pending")

        return {
            "plan": plan,
            "status": "planned",
            "approval_status": approval_status,
            "approval_required": True,
            "messages": state.get("messages", [])
            + [f"Orchestrator created a plan for task: {task}"],
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