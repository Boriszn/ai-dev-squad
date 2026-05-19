"""Tests for Orchestrator planning and approval behavior.

These tests protect the core planning contract used by the current
Plan / Act UI flow. They verify that planning returns structured data,
that empty tasks fail safely, and that approval state transitions remain
explicit and predictable.
"""

from app.agents.orchestrator import OrchestratorAgent
from app.services.task_service import build_initial_state


def test_orchestrator_creates_plan() -> None:
    """Create a structured plan for a valid task.

    This protects against regressions where planning only returns a
    plain string and forgets richer fields used by the UI.
    """
    agent = OrchestratorAgent()
    state = build_initial_state(task="Add a health endpoint.")
    result = agent.create_plan(state)

    assert result["status"] == "planned"
    assert isinstance(result["plan"], str)
    assert result["plan"]
    assert isinstance(result["plan_summary"], str)
    assert result["plan_summary"]
    assert isinstance(result["plan_steps"], list)
    assert result["plan_steps"]
    assert isinstance(result["plan_notes"], list)
    assert result["plan_notes"]
    assert isinstance(result["act_summary"], str)
    assert result["act_summary"]


def test_orchestrator_fails_safely_for_empty_task() -> None:
    """Fail safely when the input task is empty.

    This protects the workflow from starting with invalid user input.
    """
    agent = OrchestratorAgent()
    state = build_initial_state(task="   ")
    result = agent.create_plan(state)

    assert result["status"] == "failed"
    assert result["phase"] == "plan"
    assert result["approval_required"] is False
    assert result["error_message"] == "The task is empty."
    assert result["plan_steps"] == []


def test_orchestrator_check_approval_handles_approved() -> None:
    """Return an approved state update when human approval is granted."""
    agent = OrchestratorAgent()
    state = build_initial_state(task="Add a health endpoint.", approval_status="approved")
    result = agent.check_approval(state)

    assert result["status"] == "approved"
    assert result["approval_status"] == "approved"
    assert result["approval_required"] is False


def test_orchestrator_check_approval_handles_rejected() -> None:
    """Return a rejected state update when human approval is denied."""
    agent = OrchestratorAgent()
    state = build_initial_state(task="Add a health endpoint.", approval_status="rejected")
    result = agent.check_approval(state)

    assert result["status"] == "rejected"
    assert result["approval_status"] == "rejected"
    assert result["approval_required"] is False


def test_orchestrator_check_approval_handles_pending() -> None:
    """Keep waiting when approval is still pending."""
    agent = OrchestratorAgent()
    state = build_initial_state(task="Add a health endpoint.", approval_status="pending")
    result = agent.check_approval(state)

    assert result["status"] == "waiting_for_approval"
    assert result["approval_status"] == "pending"
    assert result["approval_required"] is True
