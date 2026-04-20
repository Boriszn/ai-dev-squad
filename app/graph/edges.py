"""Conditional edge helpers for AI Dev Squad.

These helpers decide where the workflow should go next based on state.
"""

from __future__ import annotations

from app.graph.state import WorkflowState


def route_after_plan(_: WorkflowState) -> str:
    """Always go from planning to approval in the MVP flow."""
    return "approval"


def route_after_approval(state: WorkflowState) -> str:
    """Route based on approval outcome."""
    status = state.get("status")
    if status == "approved":
        return "developer"
    return "end"


def route_after_development(state: WorkflowState) -> str:
    """Route based on development outcome."""
    status = state.get("status")
    if status == "developed":
        return "tester"
    return "end"


def route_after_testing(_: WorkflowState) -> str:
    """Always continue to finalize after the test step."""
    return "finalize"
