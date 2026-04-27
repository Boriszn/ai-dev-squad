"""Run the local workflow demo for AI Dev Squad.

This script starts the local workflow and prints simple progress
messages to the terminal so it is clear what is happening.

Why this script exists:
- gives a fast local way to test the workflow without Studio
- prepares a clean initial state
- runs the graph once and prints the final result
"""

from __future__ import annotations

from pathlib import Path
import sys
from pprint import pprint

# Add project root to Python path so `app` imports work
# when this script is started from the `scripts` folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import get_settings
from app.services.execution_service import run_workflow
from app.services.task_service import build_initial_state


def main() -> None:
    """Run a local demo task.

    This function loads settings, builds the initial workflow state,
    runs the workflow, and prints the final result.
    """
    print("[AI Dev Squad] Starting local workflow demo...", flush=True)

    settings = get_settings()

    # Build the initial workflow state.
    # Change these values when you want to test another scenario.
    state = build_initial_state(
        task="Create or update a file named demo_note.md with a short project note.",
        approval_status="approved",  # Try: approved / pending / rejected
        approval_note="Local demo approval",
        repo_path="/Users/boriszaikin/_Projects/my-test-repo",
        provider_name=settings.default_model_provider.lower(),
    )

    print(f"[AI Dev Squad] Task: {state['task']}", flush=True)
    print(f"[AI Dev Squad] Approval status: {state['approval_status']}", flush=True)
    print(f"[AI Dev Squad] Approval required: {state['approval_required']}", flush=True)
    print(f"[AI Dev Squad] Repo path: {state['repo_path']}", flush=True)
    print(f"[AI Dev Squad] Provider: {state['provider_name']}", flush=True)
    print("[AI Dev Squad] Running workflow...", flush=True)

    result = run_workflow(state=state, settings=settings)

    print("[AI Dev Squad] Workflow finished.", flush=True)
    print(f"[AI Dev Squad] Final status: {result.get('status')}", flush=True)
    pprint(result)


if __name__ == "__main__":
    main()