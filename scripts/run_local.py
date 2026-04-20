"""Run the local workflow demo for AI Dev Squad.

This script starts the local MVP workflow and prints simple progress
messages to the terminal so it is clear what is happening.
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
    """Run a local demo task."""
    print("[AI Dev Squad] Starting local workflow demo...", flush=True)

    settings = get_settings()
    state = build_initial_state(
        task="Create or update file named demo_note.md.",
        approval_status="approved",
        repo_path="/Users/boriszaikin/_Projects/my-test-repo",
        provider_name=settings.default_model_provider,
    )

    print(f"[AI Dev Squad] Task: {state['task']}", flush=True)
    print(f"[AI Dev Squad] Repo path: {state['repo_path']}", flush=True)
    print(
        f"[AI Dev Squad] Provider: {state['provider_name']}",
        flush=True,
    )
    print("[AI Dev Squad] Running workflow...", flush=True)

    result = run_workflow(state=state, settings=settings)

    print("[AI Dev Squad] Workflow finished.", flush=True)
    print(f"[AI Dev Squad] Final status: {result.get('status')}", flush=True)
    pprint(result)


if __name__ == "__main__":
    main()