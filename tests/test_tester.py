"""Tests for the Tester Agent."""

from app.agents.tester import TesterAgent
from app.config.settings import Settings
from app.services.task_service import build_initial_state
from app.tools.test_runner import TestRunner


def test_tester_runs_mock_tests() -> None:
    """The Tester Agent should succeed in mock mode."""
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    tester = TesterAgent(test_runner=TestRunner(settings=settings))
    state = build_initial_state(task="Run tests.", approval_status="approved")
    result = tester.execute(state)

    assert result["status"] == "tested"
    assert result["test_result"]["success"] is True
