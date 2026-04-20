"""Small demo task helper for AI Dev Squad."""

from __future__ import annotations

from app.services.task_service import build_initial_state


def main() -> None:
    """Build and print a sample workflow state."""
    state = build_initial_state(
        task="Add a simple logout endpoint and tests.",
        approval_status="approved",
        provider_name="codex",
    )
    print(state)


if __name__ == "__main__":
    main()
