"""Main entry point for running the AI Dev Squad workflow locally.

This module wires together the workflow and runs a small example task.
It is intentionally simple so the project is easy to start and debug.
"""

from __future__ import annotations

from pprint import pprint

from app.config.settings import get_settings
from app.graph.workflow import build_workflow
from app.services.task_service import build_initial_state


def main() -> None:
    """Run a simple local workflow demonstration."""
    settings = get_settings()
    workflow = build_workflow(settings=settings)

    initial_state = build_initial_state(
        task="Create a small health check endpoint and add tests.",
        approval_status="approved",
        repo_path=".",
    )

    result = workflow.invoke(initial_state)
    pprint(result)


if __name__ == "__main__":
    main()
