"""Run the local workflow demo for AI Dev Squad.

This script starts the local workflow and prints simple progress
messages to the terminal so it is clear what is happening.

Why this script exists:
- gives a fast local way to test the workflow without Studio
- prepares a clean initial state
- runs the graph once and prints the final result
- makes it easy to test both Codex and local model providers
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

    Notes:
    - For Codex, use a real repo path where file changes are allowed.
    - For the local provider, this first version is generation-only.
      It returns coding output, but does not yet apply file changes.
    """
    print("[AI Dev Squad] Starting local workflow demo...", flush=True)

    settings = get_settings()

    # Choose which provider to test.
    #
    # Recommended values:
    # - "codex" -> real local coding through Codex CLI
    # - "local" -> local Ollama-based model provider
    #
    # You can also switch back to:
    # provider_name = settings.default_model_provider.lower()
    provider_name = "local"

    # Use a task that is safe for both providers.
    # The current local provider is generation-only, so this prompt asks for
    # suggested implementation output rather than direct file changes.
    task = (
        "Review the request to add a small /health endpoint to a Python web app. "
        "Suggest which files should be created or updated, provide a short "
        "implementation plan, and include a minimal example test."
    )

    # Build the initial workflow state.
    state = build_initial_state(
        task=task,
        approval_status="approved",  # Try: approved / pending / rejected
        approval_note="Local demo approval",
        repo_path="/Users/boriszaikin/_Projects/my-test-repo",
        provider_name=provider_name,
    )

    print(f"[AI Dev Squad] Task: {state['task']}", flush=True)
    print(f"[AI Dev Squad] Approval status: {state['approval_status']}", flush=True)
    print(f"[AI Dev Squad] Approval required: {state['approval_required']}", flush=True)
    print(f"[AI Dev Squad] Repo path: {state['repo_path']}", flush=True)
    print(f"[AI Dev Squad] Provider: {state['provider_name']}", flush=True)

    if provider_name == "local":
        print(
            f"[AI Dev Squad] Local model target: {settings.local_model_name}",
            flush=True,
        )

    print("[AI Dev Squad] Running workflow...", flush=True)

    result = run_workflow(state=state, settings=settings)

    print("[AI Dev Squad] Workflow finished.", flush=True)
    print(f"[AI Dev Squad] Final status: {result.get('status')}", flush=True)

    development_result = result.get("development_result", {})
    model_status = development_result.get("model_status", {})

    if model_status:
        print("[AI Dev Squad] Model status:", flush=True)
        print(
            f"  - Tool: {model_status.get('tool', 'unknown')}",
            flush=True,
        )
        print(
            f"  - Provider: {model_status.get('provider', 'unknown')}",
            flush=True,
        )
        print(
            f"  - Backend: {model_status.get('provider_backend', 'unknown')}",
            flush=True,
        )
        print(
            f"  - Model: {model_status.get('model', 'unknown')}",
            flush=True,
        )
        print(
            f"  - Status: {model_status.get('status', 'unknown')}",
            flush=True,
        )
        print(
            f"  - Tokens used: {model_status.get('tokens_used', 'not available')}",
            flush=True,
        )

    pprint(result)


if __name__ == "__main__":
    main()