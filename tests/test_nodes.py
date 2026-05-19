"""Tests for individual workflow nodes in the Plan / Act backend flow.

These tests validate node-level behavior without relying on full graph
execution. They protect key safety rules:

- planning moves to waiting-for-approval
- approval branching is explicit
- developer is blocked without approval
- finalize produces final summary/report output
"""

from app.agents.orchestrator import OrchestratorAgent
from app.graph.nodes import (
    approval_node,
    developer_node,
    finalize_node,
    orchestrator_plan_node,
)
from app.services.task_service import build_initial_state


class _DummyDeveloper:
    """Minimal developer stub used for direct node tests.

    This keeps tests simple and avoids full model/tool wiring.
    """

    def execute(self, state):  # type: ignore[no-untyped-def]
        """Return a small developed payload for approved-path checks."""
        return {
            "status": "developed",
            "phase": "act",
            "development_result": {"success": True, "summary": "ok"},
            "messages": list(state.get("messages", [])) + ["Developer executed."],
        }


def test_orchestrator_plan_node_sets_waiting_for_approval_state() -> None:
    """Place workflow into explicit waiting-for-approval state after planning.

    This protects the new plan-card-first workflow behavior.
    """
    state = build_initial_state(task="Add endpoint")
    result = orchestrator_plan_node(state=state, orchestrator=OrchestratorAgent())

    assert result["phase"] == "plan"
    assert result["status"] == "waiting_for_approval"
    assert result["approval_status"] == "pending"
    assert result["approval_required"] is True
    assert result["action_status"] == "pending"
    assert isinstance(result["plan_steps"], list)


def test_approval_node_allows_approved_state() -> None:
    """Return approved branch output when approval status is approved."""
    state = build_initial_state(task="Add endpoint", approval_status="approved")
    result = approval_node(state=state, orchestrator=OrchestratorAgent())

    assert result["status"] == "approved"
    assert result["approval_status"] == "approved"
    assert result["approval_required"] is False
    assert result["action_status"] == "act"


def test_approval_node_stops_rejected_state() -> None:
    """Return rejected branch output when approval status is rejected."""
    state = build_initial_state(task="Add endpoint", approval_status="rejected")
    result = approval_node(state=state, orchestrator=OrchestratorAgent())

    assert result["status"] == "rejected"
    assert result["approval_status"] == "rejected"
    assert result["approval_required"] is False
    assert result["action_status"] == "reject"


def test_approval_node_keeps_pending_waiting_state() -> None:
    """Keep waiting-for-approval when no human decision exists yet."""
    state = build_initial_state(task="Add endpoint", approval_status="pending")
    result = approval_node(state=state, orchestrator=OrchestratorAgent())

    assert result["status"] == "waiting_for_approval"
    assert result["approval_status"] == "pending"
    assert result["approval_required"] is True
    assert result["action_status"] == "pending"


def test_developer_node_blocks_without_approval() -> None:
    """Block developer execution unless approval is explicitly granted.

    This protects against accidental code execution before approval.
    """
    state = build_initial_state(task="Add endpoint", approval_status="pending")
    result = developer_node(state=state, developer=_DummyDeveloper())

    assert result["status"] == "waiting_for_approval"
    assert result["phase"] == "plan"
    assert "blocked" in result["error_message"].lower()


def test_finalize_node_produces_final_summary_and_report() -> None:
    """Build final summary/report payload expected by the result UI card."""
    state = build_initial_state(task="Add endpoint", approval_status="approved")
    state["status"] = "tested"
    state["development_result"] = {
        "files_changed": ["app/api.py"],
        "what_was_added": ["health endpoint"],
        "provider": "codex",
    }
    state["test_result"] = {"summary": "All tests passed."}

    result = finalize_node(state)

    assert result["phase"] == "completed"
    assert result["current_step"] == "Finished"
    assert isinstance(result["final_summary"], str)
    assert result["final_summary"]
    assert result["final_report"]["files_changed"] == ["app/api.py"]
    assert result["final_report"]["what_was_added"] == ["health endpoint"]
    assert result["final_report"]["test_result"] == "All tests passed."
    assert isinstance(result["final_report"]["notes"], list)
