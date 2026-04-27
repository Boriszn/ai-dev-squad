"""Task service helpers for AI Dev Squad.

This module contains small helper functions for preparing workflow input.
Right now it focuses on building the initial LangGraph state.

Why this module exists:
- keeps workflow bootstrap logic out of the graph files
- creates a clean and predictable initial state
- prepares the state for Human-in-the-Loop approval flow
"""

from __future__ import annotations

from app.graph.state import WorkflowState


def build_initial_state(
    task: str,
    approval_status: str = "pending",
    repo_path: str = ".",
    provider_name: str = "codex",
    approval_note: str = "",
) -> WorkflowState:
    """Build a clean initial workflow state.

    Args:
        task: User task to execute.
        approval_status: Initial approval status for the Human-in-the-Loop gate.
            Expected values are usually:
            - pending
            - approved
            - rejected
        repo_path: Local repository path where coding and tests should run.
        provider_name: Selected coding provider.
        approval_note: Optional note for the approval step.

    Returns:
        A workflow state dictionary with the minimum fields required
        to start the workflow safely.
    """
    # Approval is required unless the caller already explicitly approved
    # or rejected the request before the workflow starts.
    approval_required = approval_status not in {"approved", "rejected"}

    return WorkflowState(
        task=task,
        plan="",
        approval_status=approval_status,
        approval_required=approval_required,
        approval_note=approval_note,
        repo_path=repo_path,
        provider_name=provider_name,
        status="created",
        messages=[],
        error_message="",
    )