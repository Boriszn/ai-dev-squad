"""Workflow builder for AI Dev Squad.

This module builds and exports the LangGraph workflow used by the project.

Why this file matters:
- It wires together the Orchestrator, Developer, and Tester agents
- It defines the workflow nodes and transitions
- It exports a compiled `graph` object so LangGraph Studio can load it

Current workflow shape:
- planning always moves to approval
- approval can continue to development
- approval can end the workflow
- pending approval ends cleanly for now
- development can continue to testing
- testing moves to finalization

Important note:
The richer Plan / Act UI is being built step by step.
For now, the graph still uses the simple backend flow:
plan -> approval -> developer -> tester -> finalize
The more advanced Act preview / confirm step will be added later.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.agents.developer import DeveloperAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.tester import TesterAgent
from app.config.settings import Settings, get_settings
from app.graph.edges import (
    route_after_approval,
    route_after_development,
    route_after_plan,
    route_after_testing,
)
from app.graph.nodes import (
    approval_node,
    developer_node,
    finalize_node,
    orchestrator_plan_node,
    tester_node,
)
from app.graph.state import WorkflowState
from app.models.codex_provider import CodexProvider
from app.models.local_provider import LocalProvider
from app.models.model_router import ModelRouter
from app.tools.test_runner import TestRunner


def build_workflow(settings: Settings):
    """Build and compile the LangGraph workflow.

    This function creates all agent objects, connects them to the required
    tools and providers, defines the graph nodes, and wires the transitions
    between steps.

    Args:
        settings: Application settings loaded from environment/config.

    Returns:
        A compiled LangGraph workflow object.
    """
    # Create the Orchestrator Agent.
    # This agent plans the work and controls the approval phase.
    orchestrator = OrchestratorAgent()

    # Create the model router used by the Developer Agent.
    # Supported providers:
    # - codex: online/local coding via Codex CLI
    # - local: Ollama-backed local model provider
    model_router = ModelRouter(
        providers={
            "codex": CodexProvider(settings=settings),
            "local": LocalProvider(settings=settings),
        },
        default_provider_name=settings.default_model_provider,
    )

    # Create the Developer Agent.
    # It uses the model router to choose the coding provider.
    developer = DeveloperAgent(model_router=model_router)

    # Create the Tester Agent.
    # It uses the local test runner to validate changes.
    tester = TesterAgent(test_runner=TestRunner(settings=settings))

    # Create the graph with the shared workflow state schema.
    graph = StateGraph(WorkflowState)

    # Register workflow nodes.
    # We use partial(...) to inject already-created agents into the node
    # functions without changing the node function signatures.
    graph.add_node(
        "orchestrator_plan",
        partial(orchestrator_plan_node, orchestrator=orchestrator),
    )
    graph.add_node(
        "approval",
        partial(approval_node, orchestrator=orchestrator),
    )
    graph.add_node(
        "developer",
        partial(developer_node, developer=developer),
    )
    graph.add_node(
        "tester",
        partial(tester_node, tester=tester),
    )
    graph.add_node("finalize", finalize_node)

    # Start the workflow with the Orchestrator planning step.
    graph.add_edge(START, "orchestrator_plan")

    # After planning, always move to the approval step.
    graph.add_conditional_edges(
        "orchestrator_plan",
        route_after_plan,
        {
            "approval": "approval",
        },
    )

    # After approval:
    # - go to Developer if approved
    # - end the workflow if approval is rejected or still pending
    #
    # Pending approval is currently handled by the UI layer, so the graph
    # should stop cleanly instead of looping.
    graph.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "developer": "developer",
            "end": END,
        },
    )

    # After development:
    # - go to Tester if development succeeded
    # - end early if development failed
    graph.add_conditional_edges(
        "developer",
        route_after_development,
        {
            "tester": "tester",
            "end": END,
        },
    )

    # After testing, continue to the finalize step.
    graph.add_conditional_edges(
        "tester",
        route_after_testing,
        {
            "finalize": "finalize",
        },
    )

    # Finalize is the last node before the workflow ends.
    graph.add_edge("finalize", END)

    # Compile the graph so it can be executed by the app or LangGraph Studio.
    return graph.compile()


# Export a compiled graph object for LangGraph Studio.
# Studio expects an exported variable named `graph` when the config points to
# `.../workflow.py:graph`.
graph = build_workflow(get_settings())