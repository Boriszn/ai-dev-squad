"""Shared workflow state for AI Dev Squad.

LangGraph uses a shared state object across nodes.
This TypedDict defines the fields used by the MVP workflow.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class WorkflowState(TypedDict, total=False):
    """State shared across the full workflow."""

    task: str
    plan: str
    approval_status: Literal["approved", "pending", "rejected"]
    status: str
    repo_path: str
    provider_name: str
    development_result: dict[str, Any]
    test_result: dict[str, Any]
    error_message: str
    messages: list[str]
