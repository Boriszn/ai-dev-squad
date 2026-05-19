"""Task service helpers for AI Dev Squad.

This module contains small helper functions for preparing workflow input.
Right now it focuses on building the initial LangGraph state.

Why this module exists:
- keeps workflow bootstrap logic out of the graph files
- creates a clean and predictable initial state
- prepares the state for the Human-in-the-Loop flow
- prepares default fields for the Plan / Act UI flow
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
        A workflow state dictionary with safe defaults for the current
        Plan / Act UI flow.
    """
    # Approval is required unless the caller already explicitly approved
    # or rejected the request before the workflow starts.
    approval_required = approval_status not in {"approved", "rejected"}

    return WorkflowState(
        # -----------------------------------------------------------------
        # Core task and workflow control
        # -----------------------------------------------------------------
        task=task,
        status="created",
        phase="plan",

        # -----------------------------------------------------------------
        # Approval and action decisions
        # -----------------------------------------------------------------
        approval_status=approval_status,
        approval_required=approval_required,
        approval_note=approval_note,
        action_status="pending",

        # -----------------------------------------------------------------
        # Planning data
        # -----------------------------------------------------------------
        plan="",
        plan_summary="",
        plan_steps=[],
        plan_notes=[],

        # -----------------------------------------------------------------
        # Act preview data
        # -----------------------------------------------------------------
        planned_file_changes={
            "create": [],
            "update": [],
        },
        act_summary="",

        # -----------------------------------------------------------------
        # Execution progress
        # -----------------------------------------------------------------
        current_step_index=0,
        total_steps=0,
        current_step="",
        step_results=[],

        # -----------------------------------------------------------------
        # Runtime configuration
        # -----------------------------------------------------------------
        repo_path=repo_path,
        provider_name=provider_name,

        # -----------------------------------------------------------------
        # Execution results
        # -----------------------------------------------------------------
        development_result={},
        test_result={},
        error_message="",
        messages=[],

        # -----------------------------------------------------------------
        # Final report
        # -----------------------------------------------------------------
        final_summary="",
        final_report={
            "files_changed": [],
            "what_was_added": [],
            "test_result": "",
            "notes": [],
        },
    )