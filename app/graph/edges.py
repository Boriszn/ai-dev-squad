"""Conditional edge helpers for AI Dev Squad.

These helpers decide where the workflow should go next based on the
current shared state.

This version is designed for a real Human-in-the-Loop flow:
- planning always moves to approval
- approval can continue, stop, or stay waiting
- development continues only if it succeeded
- testing always moves to finalize
"""

from __future__ import annotations

from app.graph.state import WorkflowState


def route_after_plan(_: WorkflowState) -> str:
    """Route after the planning step.

    The current design always moves from the Orchestrator planning step
    to the approval step.

    Args:
        _: Shared workflow state. It is not needed here because the
            next step is always the same.

    Returns:
        The name of the next workflow node.
    """
    return "approval"


def route_after_approval(state: WorkflowState) -> str:
    """Route based on the current approval state.

    Possible outcomes:
    - approved -> continue to developer
    - rejected -> stop the workflow
    - waiting_for_approval / pending -> stay on approval

    Args:
        state: Shared workflow state.

    Returns:
        The name of the next workflow node or end marker key.
    """
    status = state.get("status")
    approval_status = state.get("approval_status")

    # Explicit human approval allows development to start.
    if status == "approved" or approval_status == "approved":
        return "developer"

    # Explicit rejection ends the workflow.
    if status == "rejected" or approval_status == "rejected":
        return "end"

    # Default path: still waiting for human decision.
    return "approval"


def route_after_development(state: WorkflowState) -> str:
    """Route based on the development outcome.

    The Developer Agent is expected to set a development-related status.
    If development completed successfully, continue to testing.
    Otherwise stop the workflow.

    Args:
        state: Shared workflow state.

    Returns:
        The name of the next workflow node or end marker key.
    """
    status = state.get("status")

    if status == "developed":
        return "tester"

    return "end"


def route_after_testing(_: WorkflowState) -> str:
    """Route after the test step.

    The current design always moves from testing to the finalize node.

    Args:
        _: Shared workflow state. It is not needed here because the
            next step is always the same.

    Returns:
        The name of the next workflow node.
    """
    return "finalize"