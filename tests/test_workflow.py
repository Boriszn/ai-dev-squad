"""Workflow integration tests for the current Plan / Act backend flow.

These tests verify that the compiled graph follows the intended simple
sequence:

- orchestrator_plan -> approval -> developer -> tester -> finalize

They also protect the critical non-looping behavior for pending approval.
Pending and rejected decisions must stop cleanly instead of recursively
re-entering the approval node.
"""

from app.config.settings import Settings
from app.graph.workflow import build_workflow
from app.services.task_service import build_initial_state


def test_workflow_runs_to_finalize_when_approved() -> None:
    """Run the full happy path when approval is already granted.

    This protects against regressions where the workflow would stop too
    early and skip finalization output fields used by the UI result card.
    """
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    workflow = build_workflow(settings=settings)

    state = build_initial_state(
        task="Add a test file.",
        approval_status="approved",
    )
    result = workflow.invoke(state)

    assert result["status"] == "tested"
    assert result["phase"] == "completed"
    assert isinstance(result["final_summary"], str)
    assert result["final_summary"]
    assert isinstance(result["final_report"], dict)
    assert "files_changed" in result["final_report"]
    assert "what_was_added" in result["final_report"]
    assert "test_result" in result["final_report"]
    assert "notes" in result["final_report"]
    assert "Workflow finished." in result["messages"]


def test_workflow_stops_when_not_approved() -> None:
    """Stop cleanly in pending state without entering development.

    This protects the no-recursion fix for pending approvals.
    """
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    workflow = build_workflow(settings=settings)

    state = build_initial_state(
        task="Add a test file.",
        approval_status="pending",
    )
    result = workflow.invoke(state)

    assert result["status"] == "waiting_for_approval"
    assert result["approval_status"] == "pending"
    assert result["approval_required"] is True
    assert "development_result" not in result or result["development_result"] == {}
    assert "Workflow finished." not in result.get("messages", [])


def test_workflow_stops_cleanly_when_rejected() -> None:
    """Stop cleanly when approval is rejected.

    This protects against accidentally continuing to developer/tester when
    the user explicitly rejects the plan.
    """
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    workflow = build_workflow(settings=settings)

    state = build_initial_state(
        task="Add a test file.",
        approval_status="rejected",
    )
    result = workflow.invoke(state)

    assert result["status"] == "rejected"
    assert result["approval_status"] == "rejected"
    assert result["approval_required"] is False
    assert "development_result" not in result or result["development_result"] == {}
    assert "Workflow finished." not in result.get("messages", [])
