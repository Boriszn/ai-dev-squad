"""Tests for the Orchestrator Agent."""

from app.agents.orchestrator import OrchestratorAgent
from app.services.task_service import build_initial_state


def test_orchestrator_creates_plan() -> None:
    """The Orchestrator should create a plan for a valid task."""
    agent = OrchestratorAgent()
    state = build_initial_state(task="Add a health endpoint.")
    result = agent.create_plan(state)

    assert result["status"] == "planned"
    assert "plan" in result


def test_orchestrator_blocks_when_not_approved() -> None:
    """The workflow should wait when approval was not granted."""
    agent = OrchestratorAgent()
    state = build_initial_state(task="Add a health endpoint.", approval_status="pending")
    result = agent.check_approval(state)

    assert result["status"] == "waiting_for_approval"
