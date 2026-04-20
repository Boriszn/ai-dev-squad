"""Graph nodes for AI Dev Squad.

Each node is a small function that calls one agent or one service.
This keeps the workflow readable and easy to test.
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
    """Create the plan for the current task."""
    return orchestrator.create_plan(state)


def approval_node(
    state: WorkflowState,
    orchestrator: OrchestratorAgent,
) -> dict[str, object]:
    """Check whether approval has been granted."""
    return orchestrator.check_approval(state)


def developer_node(
    state: WorkflowState,
    developer: DeveloperAgent,
) -> dict[str, object]:
    """Run the development step."""
    return developer.execute(state)


def tester_node(
    state: WorkflowState,
    tester: TesterAgent,
) -> dict[str, object]:
    """Run the test step."""
    return tester.execute(state)


def finalize_node(state: WorkflowState) -> dict[str, object]:
    """Prepare the final state message.

    This node is intentionally small. It can later be expanded into a
    richer summarizer or reporting agent.
    """
    messages = state.get("messages", [])
    messages.append("Workflow finished.")
    return {"messages": messages}
