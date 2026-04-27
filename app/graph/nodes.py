"""Graph nodes for AI Dev Squad.

Each node is a small function that calls one agent or handles one step
of the workflow. This keeps the graph readable, testable, and easy to
change.

This version adds clearer Human-in-the-Loop behavior:
- the planning step prepares the workflow for approval
- the approval step can hold the workflow in a waiting state
- the developer step is guarded so code work does not start without approval
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

    This node calls the Orchestrator Agent and then normalizes the state
    so the workflow clearly enters the approval phase.

    Args:
        state: Shared workflow state.
        orchestrator: Orchestrator Agent instance.

    Returns:
        A partial state update with the plan and approval-related fields.
    """
    result = orchestrator.create_plan(state)

    # Start from the messages returned by the Orchestrator if present.
    messages = list(result.get("messages", state.get("messages", [])))

    # If the caller did not already set approval status, default to pending.
    approval_status = state.get("approval_status", "pending")

    # Add a clear message so the next step is visible in logs and Studio.
    messages.append("Plan created. Waiting for human approval.")

    return {
        **result,
        "approval_status": approval_status,
        "approval_required": True,
        "status": "waiting_for_approval",
        "messages": messages,
    }


def approval_node(
    state: WorkflowState,
    orchestrator: OrchestratorAgent,
) -> dict[str, object]:
    """Evaluate the current approval state.

    This node does not start development. It only decides whether the
    workflow should continue, wait, or stop based on the current
    approval status in state.

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
            "status": "approved",
            "messages": messages,
        }

    if approval_status == "rejected":
        messages.append("Human approval was rejected. Workflow will stop.")
        return {
            "approval_status": "rejected",
            "approval_required": False,
            "status": "rejected",
            "messages": messages,
        }

    # Default path: still waiting for a human decision.
    messages.append("Still waiting for human approval.")
    return {
        "approval_status": "pending",
        "approval_required": True,
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
            "status": "waiting_for_approval",
            "messages": messages,
            "error_message": "Development blocked until approval is granted.",
        }

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
    return tester.execute(state)


def finalize_node(state: WorkflowState) -> dict[str, object]:
    """Prepare the final state message.

    This node is intentionally small. It can later be expanded into a
    richer summarizer or reporting agent.

    Args:
        state: Shared workflow state.

    Returns:
        A partial state update with the final message.
    """
    messages = list(state.get("messages", []))
    messages.append("Workflow finished.")
    return {"messages": messages}