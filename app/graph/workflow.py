"""Workflow builder for AI Dev Squad.

This module creates the LangGraph workflow used by the MVP.
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.agents.developer import DeveloperAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.tester import TesterAgent
from app.config.settings import Settings
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

    Args:
        settings: Application settings.

    Returns:
        A compiled LangGraph application.
    """
    orchestrator = OrchestratorAgent()
    model_router = ModelRouter(
        providers={
            "codex": CodexProvider(settings=settings),
            "local": LocalProvider(settings=settings),
        },
        default_provider_name=settings.default_model_provider,
    )
    developer = DeveloperAgent(model_router=model_router)
    tester = TesterAgent(test_runner=TestRunner(settings=settings))

    graph = StateGraph(WorkflowState)

    graph.add_node("orchestrator_plan", partial(orchestrator_plan_node, orchestrator=orchestrator))
    graph.add_node("approval", partial(approval_node, orchestrator=orchestrator))
    graph.add_node("developer", partial(developer_node, developer=developer))
    graph.add_node("tester", partial(tester_node, tester=tester))
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "orchestrator_plan")
    graph.add_conditional_edges(
        "orchestrator_plan",
        route_after_plan,
        {
            "approval": "approval",
        },
    )
    graph.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "developer": "developer",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "developer",
        route_after_development,
        {
            "tester": "tester",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "tester",
        route_after_testing,
        {
            "finalize": "finalize",
        },
    )
    graph.add_edge("finalize", END)

    return graph.compile()
