"""Orchestrator agent for AI Dev Squad.

The Orchestrator is the control point of the workflow.
It receives the task, creates a simple plan, and decides whether the
next step should be approval, development, or termination.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.graph.state import WorkflowState


@dataclass
class OrchestratorAgent:
    """Plan and route the user task."""

    def create_plan(self, state: WorkflowState) -> dict[str, Any]:
        """Create a simple execution plan from the current task.

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with the execution plan.
        """
        task = state.get("task", "").strip()
        if not task:
            return {
                "plan": "No task provided.",
                "status": "failed",
                "error_message": "The task is empty.",
            }

        plan = (
            "1. Review the task. "
            "2. Ask for approval before changes. "
            "3. Send approved task to the Developer Agent. "
            "4. Run the Tester Agent. "
            "5. Return the result."
        )
        return {
            "plan": plan,
            "status": "planned",
            "messages": state.get("messages", [])
            + [f"Orchestrator created a plan for task: {task}"],
        }

    def check_approval(self, state: WorkflowState) -> dict[str, Any]:
        """Evaluate the approval status.

        Args:
            state: Shared workflow state.

        Returns:
            A partial state update with the approval result.
        """
        approval_status = (state.get("approval_status") or "").lower().strip()

        if approval_status == "approved":
            return {
                "status": "approved",
                "messages": state.get("messages", [])
                + ["Approval granted. The workflow can continue."],
            }

        return {
            "status": "waiting_for_approval",
            "messages": state.get("messages", [])
            + ["Approval not granted yet. Workflow stopped before development."],
        }
