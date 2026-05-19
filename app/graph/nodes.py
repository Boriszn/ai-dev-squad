"""Graph nodes for AI Dev Squad.

Each node is a small function that calls one agent or handles one step
of the workflow. This keeps the graph readable, testable, and easy to
change.

This version adds support for the richer Plan / Act flow:
- the planning step prepares structured plan data
- the approval step keeps the workflow safe
- the developer step is still guarded by approval
- execution fields are prepared for progress tracking
"""

from __future__ import annotations

from app.agents.developer import DeveloperAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.tester import TesterAgent
from app.graph.state import WorkflowState


def orchestrator_plan_node(
    state: WorkflowState,
    orchestrator: OrchestratorAgent,
) -> dict[str, object]:
    """Create the plan for the current task.

    This node calls the Orchestrator Agent and normalizes the state so
    the workflow clearly enters the Plan / Act approval phase.

    Args:
        state: Shared workflow state.
        orchestrator: Orchestrator Agent instance.

    Returns:
        A partial state update with plan and approval-related fields.
    """
    result = orchestrator.create_plan(state)

    # Start from the messages returned by the Orchestrator if present.
    messages = list(result.get("messages", state.get("messages", [])))

    # If the caller did not already set approval status, default to pending.
    approval_status = state.get("approval_status", "pending")

    # Make the next state explicit for the UI.
    messages.append("Plan created. Waiting for human approval.")

    return {
        **result,
        "phase": "plan",
        "approval_status": approval_status,
        "approval_required": True,
        "action_status": "pending",
        "status": "waiting_for_approval",
        "messages": messages,
    }


def approval_node(
    state: WorkflowState,
    orchestrator: OrchestratorAgent,
) -> dict[str, object]:
    """Evaluate the current approval state.

    This node does not start development. It only decides whether the
    workflow can continue or should stop based on approval status.

    Args:
        state: Shared workflow state.
        orchestrator: Orchestrator Agent instance.
            Kept here for consistency and future extension.

    Returns:
        A partial state update with approval decision fields.
    """
    # The Orchestrator is not actively used here yet, but we keep the
    # argument because the workflow already injects it into this node.
    _ = orchestrator

    messages = list(state.get("messages", []))
    approval_status = state.get("approval_status", "pending")

    if approval_status == "approved":
        messages.append("Human approval received. Development can start.")
        return {
            "approval_status": "approved",
            "approval_required": False,
            "action_status": "act",
            "status": "approved",
            "messages": messages,
        }

    if approval_status == "rejected":
        messages.append("Human approval was rejected. Workflow will stop.")
        return {
            "approval_status": "rejected",
            "approval_required": False,
            "action_status": "reject",
            "status": "rejected",
            "messages": messages,
        }

    # Default path: still waiting for a human decision.
    messages.append("Still waiting for human approval.")
    return {
        "approval_status": "pending",
        "approval_required": True,
        "action_status": "pending",
        "status": "waiting_for_approval",
        "messages": messages,
    }


def developer_node(
    state: WorkflowState,
    developer: DeveloperAgent,
) -> dict[str, object]:
    """Run the development step.

    This node is guarded. It refuses to run development unless the
    workflow has explicit approval.

    Args:
        state: Shared workflow state.
        developer: Developer Agent instance.

    Returns:
        A partial state update from the Developer Agent, or a safe guard
        response if approval is missing.
    """
    approval_status = state.get("approval_status", "pending")

    # Do not allow code changes unless the workflow is explicitly approved.
    if approval_status != "approved":
        messages = list(state.get("messages", []))
        messages.append("Developer step blocked because approval is missing.")
        return {
            "phase": "plan",
            "status": "waiting_for_approval",
            "messages": messages,
            "error_message": "Development blocked until approval is granted.",
        }

    # Mark progress fields before the Developer Agent runs.
    # The Developer Agent result will overwrite or extend these fields later.
    state["phase"] = "act"
    state["current_step_index"] = max(state.get("current_step_index", 0), 1)
    state["current_step"] = "Running developer step"

    return developer.execute(state)


def tester_node(
    state: WorkflowState,
    tester: TesterAgent,
) -> dict[str, object]:
    """Run the test step.

    Args:
        state: Shared workflow state.
        tester: Tester Agent instance.

    Returns:
        A partial state update from the Tester Agent.
    """
    # Mark progress fields before the Tester Agent runs.
    state["phase"] = "act"
    state["current_step_index"] = max(state.get("current_step_index", 0), 2)
    state["current_step"] = "Running test step"

    return tester.execute(state)


def finalize_node(state: WorkflowState) -> dict[str, object]:
    """Prepare the final state message and final report fields.

    This node is intentionally simple for now, but it already prepares
    output that the future Task Completed card can use.

    Args:
        state: Shared workflow state.

    Returns:
        A partial state update with the final message and final report fields.
    """
    messages = list(state.get("messages", []))
    messages.append("Workflow finished.")

    development_result = state.get("development_result", {}) or {}
    test_result = state.get("test_result", {}) or {}

    final_summary = "Task completed."
    if state.get("status") == "test_failed":
        final_summary = "Task finished, but tests failed."
    elif state.get("status") == "development_failed":
        final_summary = "Task stopped because development failed."
    elif state.get("status") == "tested":
        final_summary = "Task completed successfully."

    final_report = {
        "files_changed": development_result.get("files_changed", []),
        "what_was_added": development_result.get("what_was_added", []),
        "test_result": test_result.get("summary", ""),
        "notes": [],
    }

    # Add simple notes that the future completed card can show.
    if development_result.get("provider") == "local":
        final_report["notes"].append(
            "Local provider is currently generation-only and may not apply file changes yet."
        )

    return {
        "phase": "completed",
        "current_step": "Finished",
        "final_summary": final_summary,
        "final_report": final_report,
        "messages": messages,
    }