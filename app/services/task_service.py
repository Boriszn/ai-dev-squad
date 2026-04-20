"""Task service helpers for AI Dev Squad."""

from __future__ import annotations

from app.graph.state import WorkflowState


def build_initial_state(
    task: str,
    approval_status: str = "pending",
    repo_path: str = ".",
    provider_name: str = "codex",
) -> WorkflowState:
    """Build a clean initial workflow state.

    Args:
        task: User task to execute.
        approval_status: Approval status for the HIL gate.
        repo_path: Local repository path.
        provider_name: Selected coding provider.

    Returns:
        A workflow state dictionary.
    """
    return WorkflowState(
        task=task,
        approval_status=approval_status,
        repo_path=repo_path,
        provider_name=provider_name,
        status="created",
        messages=[],
    )
