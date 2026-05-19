"""Tests for task bootstrap helpers and initial workflow state defaults.

These tests protect the state contract created by `build_initial_state(...)`.
The Plan / Act UI and workflow nodes rely on these defaults being present,
so this file ensures new fields remain available with safe initial values.
"""

from app.services.task_service import build_initial_state


def test_build_initial_state_includes_plan_act_defaults() -> None:
    """Build initial state with all expected Plan / Act defaults.

    This test protects against missing fields that would break planning cards,
    approval handling, progress views, or final report rendering.
    """
    state = build_initial_state(task="Add health endpoint")

    assert state["phase"] == "plan"
    assert state["action_status"] == "pending"
    assert state["plan_summary"] == ""
    assert state["plan_steps"] == []
    assert state["plan_notes"] == []
    assert state["planned_file_changes"] == {"create": [], "update": []}
    assert state["current_step_index"] == 0
    assert state["total_steps"] == 0
    assert state["current_step"] == ""
    assert state["step_results"] == []
    assert state["final_summary"] == ""

    assert state["final_report"] == {
        "files_changed": [],
        "what_was_added": [],
        "test_result": "",
        "notes": [],
    }


def test_build_initial_state_sets_approval_required_for_pending_only() -> None:
    """Set `approval_required` based on the initial approval status.

    Pending requests require approval, while pre-approved and pre-rejected
    runs should not require another decision at bootstrap time.
    """
    pending_state = build_initial_state(task="A", approval_status="pending")
    approved_state = build_initial_state(task="A", approval_status="approved")
    rejected_state = build_initial_state(task="A", approval_status="rejected")

    assert pending_state["approval_required"] is True
    assert approved_state["approval_required"] is False
    assert rejected_state["approval_required"] is False
