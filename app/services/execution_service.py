"""Execution helpers for AI Dev Squad.

This module is a small place for orchestration helpers that sit outside
the graph file. It keeps the main workflow code tidy.
"""

from __future__ import annotations

from app.config.settings import Settings
from app.graph.workflow import build_workflow
from app.graph.state import WorkflowState


def run_workflow(state: WorkflowState, settings: Settings):
    """Run the compiled workflow with the provided state."""
    workflow = build_workflow(settings=settings)
    return workflow.invoke(state)
