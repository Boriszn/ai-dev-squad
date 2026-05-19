"""Tests for Tester Agent behavior in mock execution mode.

This file verifies the basic contract of the tester step: it should run
the configured test runner and return a successful structured result in
mock mode, which keeps workflow integration deterministic in tests.
"""

from app.agents.tester import TesterAgent
from app.config.settings import Settings
from app.services.task_service import build_initial_state
from app.tools.test_runner import TestRunner


def test_tester_runs_mock_tests() -> None:
    """Run mock tests successfully and return structured test output.

    This protects against regressions where the tester step no longer
    reports success flags in the expected shape.
    """
    settings = Settings(ENABLE_MOCK_TOOLS=True)
    tester = TesterAgent(test_runner=TestRunner(settings=settings))
    state = build_initial_state(task="Run tests.", approval_status="approved")
    result = tester.execute(state)

    assert result["status"] == "tested"
    assert result["test_result"]["success"] is True
