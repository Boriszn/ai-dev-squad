"""Shared workflow state for AI Dev Squad.

LangGraph uses a shared state object across nodes.
This TypedDict defines the fields used by the workflow.

Why this state was extended:
- to support a richer Plan / Act user flow
- to keep plan, preview, execution, and final report data in one place
- to support future progress tracking in the UI
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class WorkflowState(TypedDict, total=False):
    """State shared across the full workflow.

    This object moves through all graph nodes and stores the
    current task, planning data, approval data, execution results,
    and user-facing report data.
    """

    # -------------------------------------------------------------------------
    # Core task and workflow control
    # -------------------------------------------------------------------------

    # Main user task passed into the workflow.
    task: str

    # Current high-level workflow status.
    #
    # Example values:
    # - created
    # - planned
    # - waiting_for_approval
    # - waiting_for_action
    # - act_preview_ready
    # - approved
    # - rejected
    # - cancelled
    # - developing
    # - developed
    # - development_failed
    # - testing
    # - tested
    # - test_failed
    # - finished
    status: str

    # Current phase of the Plan / Act flow.
    #
    # Example values:
    # - plan
    # - act_preview
    # - act
    # - completed
    phase: Literal["plan", "act_preview", "act", "completed"]

    # -------------------------------------------------------------------------
    # Approval and action decisions
    # -------------------------------------------------------------------------

    # Human approval status for the workflow.
    # - pending: waiting for a decision
    # - approved: human approved the next step
    # - rejected: human rejected the next step
    approval_status: Literal["approved", "pending", "rejected"]

    # Flag showing whether the workflow currently requires
    # a human approval decision before continuing.
    approval_required: bool

    # Optional note attached to the approval step.
    approval_note: str

    # User action for the Plan / Act flow.
    #
    # Example values:
    # - pending
    # - act
    # - confirm
    # - reject
    # - cancel
    action_status: Literal["pending", "act", "confirm", "reject", "cancel"]

    # -------------------------------------------------------------------------
    # Planning data
    # -------------------------------------------------------------------------

    # Simple full plan text created by the Orchestrator Agent.
    plan: str

    # Short summary for the plan card in the UI.
    plan_summary: str

    # Structured numbered steps for the plan card.
    plan_steps: list[str]

    # Optional notes, warnings, or scope details for the plan.
    plan_notes: list[str]

    # -------------------------------------------------------------------------
    # Act preview data
    # -------------------------------------------------------------------------

    # File preview before execution.
    # The structure can stay flexible for now.
    #
    # Example:
    # {
    #   "create": ["app/api/health.py", "tests/test_health.py"],
    #   "update": ["README.md"]
    # }
    planned_file_changes: dict[str, list[str]]

    # Short summary for the act preview card.
    act_summary: str

    # -------------------------------------------------------------------------
    # Execution progress
    # -------------------------------------------------------------------------

    # Current step number during execution.
    current_step_index: int

    # Total number of planned execution steps.
    total_steps: int

    # Current active step label shown in the UI.
    current_step: str

    # Per-step execution results collected during the run.
    step_results: list[dict[str, Any]]

    # -------------------------------------------------------------------------
    # Runtime configuration
    # -------------------------------------------------------------------------

    # Local repository path where coding and tests should run.
    repo_path: str

    # Name of the selected provider used by the Developer Agent.
    # Example values:
    # - codex
    # - local
    provider_name: str

    # -------------------------------------------------------------------------
    # Execution results
    # -------------------------------------------------------------------------

    # Structured result returned by the Developer Agent.
    development_result: dict[str, Any]

    # Structured result returned by the Tester Agent.
    test_result: dict[str, Any]

    # Optional workflow-level error message.
    error_message: str

    # Human-readable workflow messages collected across nodes.
    messages: list[str]

    # -------------------------------------------------------------------------
    # Final report
    # -------------------------------------------------------------------------

    # Final task summary shown in the completed card.
    final_summary: str

    # Final report object for the Task Completed card.
    #
    # Example:
    # {
    #   "files_changed": [...],
    #   "what_was_added": [...],
    #   "test_result": "...",
    #   "notes": [...]
    # }
    final_report: dict[str, Any]