"""Lightweight tests for stable UI helper logic in Streamlit components.

These tests intentionally focus on pure helper behavior that is easy to
keep stable over time. They avoid deep Streamlit rendering mocks and only
verify status-to-progress mapping used by the sidebar progress panel.
"""

from app.ui.components import map_status_to_progress


def test_map_status_to_progress_for_plan_states() -> None:
    """Map planning-related statuses to the planning progress bucket."""
    assert map_status_to_progress("created") == (0.2, "Planning")
    assert map_status_to_progress("planned") == (0.2, "Planning")


def test_map_status_to_progress_for_waiting_approval_states() -> None:
    """Map waiting statuses to the approval waiting bucket."""
    assert map_status_to_progress("waiting_for_approval") == (0.4, "Waiting for approval")
    assert map_status_to_progress("pending") == (0.4, "Waiting for approval")


def test_map_status_to_progress_for_developing_testing_and_finished() -> None:
    """Map execution statuses to expected developing/testing/finished buckets."""
    assert map_status_to_progress("approved") == (0.6, "Developing")
    assert map_status_to_progress("developed") == (0.8, "Testing")
    assert map_status_to_progress("tested") == (0.8, "Testing")
    assert map_status_to_progress("completed") == (1.0, "Finished")


def test_map_status_to_progress_for_rejected_and_failed_states() -> None:
    """Expose stopped labels for rejected or failed workflow statuses."""
    assert map_status_to_progress("rejected") == (0.4, "Stopped: rejected")
    assert map_status_to_progress("failed") == (0.8, "Stopped: failed")
