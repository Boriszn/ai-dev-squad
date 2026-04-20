"""Workflow integration tests."""

from app.config.settings import Settings
from app.graph.workflow import build_workflow
from app.services.task_service import build_initial_state


def test_workflow_runs_to_finalize_when_approved() -> None:
    """The workflow should reach finalize when approval is granted."""
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    workflow = build_workflow(settings=settings)

    state = build_initial_state(
        task="Add a test file.",
        approval_status="approved",
    )
    result = workflow.invoke(state)

    assert result["status"] == "tested"
    assert "Workflow finished." in result["messages"]


def test_workflow_stops_when_not_approved() -> None:
    """The workflow should stop before development without approval."""
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    workflow = build_workflow(settings=settings)

    state = build_initial_state(
        task="Add a test file.",
        approval_status="pending",
    )
    result = workflow.invoke(state)

    assert result["status"] == "waiting_for_approval"
