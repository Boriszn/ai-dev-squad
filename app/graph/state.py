"""Shared workflow state for AI Dev Squad.

LangGraph uses a shared state object across nodes.
This TypedDict defines the fields used by the workflow.

Why this state was extended:
- to support a real Human-in-the-Loop approval step
- to keep approval-related data in one place
- to make pause/resume behavior easier later
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class WorkflowState(TypedDict, total=False):
    """State shared across the full workflow.

    This object moves through all graph nodes and stores the
    current task, planning data, approval data, execution results,
    and human-readable messages.
    """

    # Main user task passed into the workflow.
    task: str

    # Simple execution plan created by the Orchestrator Agent.
    plan: str

    # Human approval status for the workflow.
    # - pending: waiting for a decision
    # - approved: human approved the next step
    # - rejected: human rejected the next step
    approval_status: Literal["approved", "pending", "rejected"]

    # Flag showing whether the workflow currently requires
    # a human approval decision before continuing.
    approval_required: bool

    # Optional note attached to the approval step.
    # This can later store short human feedback such as:
    # "approved for docs only" or "rejected, needs more detail".
    approval_note: str

    # High-level workflow status.
    # Examples:
    # - planning
    # - waiting_for_approval
    # - approved
    # - rejected
    # - developing
    # - development_failed
    # - testing
    # - test_failed
    # - tested
    # - finished
    status: str

    # Local repository path where coding and tests should run.
    repo_path: str

    # Name of the selected provider used by the Developer Agent.
    # Example values:
    # - codex
    # - local
    provider_name: str

    # Structured result returned by the Developer Agent.
    development_result: dict[str, Any]

    # Structured result returned by the Tester Agent.
    test_result: dict[str, Any]

    # Optional error message for workflow-level failures.
    error_message: str

    # Human-readable workflow messages collected across nodes.
    messages: list[str]