"""Chat-style Streamlit UI for AI Dev Squad.

This module provides a chat-like local control panel for running the
AI Dev Squad workflow without using LangGraph Studio.

Current goals:
- accept a user task through chat input
- generate a structured plan first
- show an Act preview before execution
- ask for human confirmation with buttons
- run the workflow only after confirmation
- show final result as assistant messages
- support both Codex and local provider selection from the UI

Important note:
The current graph does not yet use a true interrupt/resume approval flow.
Because of that, this UI handles the Plan / Act interaction at the UI layer:
- first build the plan only
- then show an Act preview
- then run the full workflow after confirmation

Local provider note:
The first local provider version is generation-only.
It can return implementation guidance and code suggestions, but it does
not directly apply file changes yet.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import streamlit as st

# Add project root to Python path so imports work when Streamlit runs
# this file directly from the app/ui folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.orchestrator import OrchestratorAgent
from app.config.settings import Settings, get_settings
from app.services.execution_service import run_workflow
from app.services.task_service import build_initial_state
from app.ui.components import (
    render_chat_message,
    render_confirm_action_bar,
    render_plan_action_bar,
    render_sidebar_progress_panel,
)


def initialize_session_state() -> None:
    """Initialize Streamlit session state keys used by the chat UI."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "pending_request" not in st.session_state:
        st.session_state.pending_request = None

    if "request_counter" not in st.session_state:
        st.session_state.request_counter = 0

    if "sidebar_repo_path" not in st.session_state:
        st.session_state.sidebar_repo_path = "."

    if "sidebar_provider_name" not in st.session_state:
        st.session_state.sidebar_provider_name = "codex"

    if "sidebar_approval_note" not in st.session_state:
        st.session_state.sidebar_approval_note = ""

    if "sidebar_run_snapshot" not in st.session_state:
        st.session_state.sidebar_run_snapshot = {
            "status": "idle",
            "provider_name": st.session_state.sidebar_provider_name,
            "model_status": {},
        }


def update_sidebar_run_snapshot(data: dict[str, Any]) -> None:
    """Merge a partial run snapshot into sidebar state.

    Args:
        data: Partial snapshot fields to merge into current sidebar snapshot.
    """
    current = dict(st.session_state.sidebar_run_snapshot)
    current.update(data)
    st.session_state.sidebar_run_snapshot = current


def add_user_message(content: str) -> None:
    """Append a user message to chat history.

    Args:
        content: User message text.
    """
    st.session_state.chat_history.append(
        {
            "role": "user",
            "kind": "text",
            "content": content,
        }
    )


def add_assistant_message(
    content: str,
    kind: str = "text",
    data: dict[str, Any] | None = None,
) -> None:
    """Append an assistant message to chat history.

    Args:
        content: Assistant message text.
        kind: Message kind such as text, plan, act_preview, progress, or result.
        data: Optional structured data attached to the message.
    """
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "kind": kind,
            "content": content,
            "data": data or {},
        }
    )


def clear_pending_request() -> None:
    """Clear the current pending request from session state."""
    st.session_state.pending_request = None


def build_plan_preview(
    task: str,
    repo_path: str,
    provider_name: str,
    approval_note: str,
) -> dict[str, Any]:
    """Build a planning-only preview result.

    This uses the Orchestrator Agent to generate a plan without starting
    development or testing.

    Args:
        task: User task text.
        repo_path: Target repository path.
        provider_name: Selected provider name.
        approval_note: Optional approval note.

    Returns:
        A structured plan preview dictionary.
    """
    orchestrator = OrchestratorAgent()

    state = build_initial_state(
        task=task,
        approval_status="pending",
        repo_path=repo_path,
        provider_name=provider_name,
        approval_note=approval_note,
    )

    plan_result = orchestrator.create_plan(state)

    messages = list(plan_result.get("messages", []))
    messages.append("Plan is ready.")
    messages.append("Use Act, Reject, or Cancel to continue.")

    # Add a local-provider note so the UI is clear before execution.
    if provider_name == "local":
        messages.append(
            "Local provider is in generation-only mode. "
            "It can suggest implementation output, but it does not write files yet."
        )

    return {
        **state,
        **plan_result,
        "phase": "plan",
        "status": "waiting_for_action",
        "approval_status": "pending",
        "approval_required": True,
        "action_status": "pending",
        "messages": messages,
    }


def infer_planned_file_changes(task: str) -> dict[str, list[str]]:
    """Infer a simple file preview from the task text.

    This is a lightweight UI-first preview helper.
    It does not inspect the repository yet. It only gives the user a
    simple preview card until we introduce a real repo-aware preview step.

    Args:
        task: User task text.

    Returns:
        A dictionary with "create" and "update" file lists.
    """
    task_lower = task.lower()

    create_files: list[str] = []
    update_files: list[str] = []

    # Simple API/endpoint heuristics.
    if any(keyword in task_lower for keyword in ["endpoint", "api", "/health", "route", "fastapi", "flask"]):
        update_files.append("app.py")
        create_files.append("tests/test_health.py")

    # Docs-related heuristics.
    if any(keyword in task_lower for keyword in ["readme", "docs", "documentation", ".md"]):
        update_files.append("README.md")

    # Test-related heuristics.
    if any(keyword in task_lower for keyword in ["test", "tests", "pytest"]) and "tests/test_health.py" not in create_files:
        create_files.append("tests/test_feature.py")

    # Generic code change fallback if nothing matched.
    if not create_files and not update_files:
        update_files.append("app/main.py")
        create_files.append("tests/test_feature.py")

    return {
        "create": create_files,
        "update": update_files,
    }


def build_act_preview(
    task: str,
    repo_path: str,
    provider_name: str,
    approval_note: str,
    plan_preview: dict[str, Any],
) -> dict[str, Any]:
    """Build an Act preview before execution starts.

    This is still a UI-layer preview for now. It prepares the card that
    shows the likely file changes before the user confirms execution.

    Args:
        task: User task text.
        repo_path: Target repository path.
        provider_name: Selected provider name.
        approval_note: Optional approval note.
        plan_preview: Existing plan preview data.

    Returns:
        A structured act preview dictionary.
    """
    planned_file_changes = plan_preview.get("planned_file_changes") or infer_planned_file_changes(task)
    messages = list(plan_preview.get("messages", []))

    messages.append("Act preview is ready.")
    messages.append("Review the planned file changes and confirm to continue.")

    notes = list(plan_preview.get("plan_notes", []))
    notes.append("File preview is currently a UI-first estimate, not a repo-aware diff yet.")

    act_summary = plan_preview.get("act_summary") or (
        "Review the target files and confirm changes before execution starts."
    )

    return {
        **plan_preview,
        "phase": "act_preview",
        "status": "act_preview_ready",
        "action_status": "act",
        "planned_file_changes": planned_file_changes,
        "plan_notes": notes,
        "act_summary": act_summary,
        "messages": messages,
    }


def build_progress_snapshot(
    task: str,
    repo_path: str,
    provider_name: str,
    total_steps: int,
) -> dict[str, Any]:
    """Build a lightweight progress payload shown before execution finishes.

    Args:
        task: User task text.
        repo_path: Target repository path.
        provider_name: Selected provider name.
        total_steps: Total planned steps.

    Returns:
        A progress data dictionary for the progress card.
    """
    return {
        "task": task,
        "repo_path": repo_path,
        "provider_name": provider_name,
        "phase": "act",
        "status": "developing",
        "approval_status": "approved",
        "current_step_index": 1,
        "total_steps": max(total_steps, 2),
        "current_step": "Running developer step",
        "step_results": [
            {
                "step": "developer",
                "status": "started",
                "message": "Developer step has started.",
            }
        ],
    }


def execute_approved_workflow(
    task: str,
    repo_path: str,
    provider_name: str,
    approval_note: str,
) -> dict[str, Any]:
    """Run the full workflow after approval.

    Args:
        task: User task text.
        repo_path: Target repository path.
        provider_name: Selected provider name.
        approval_note: Optional approval note.

    Returns:
        Final workflow result dictionary.
    """
    settings = get_settings()

    state = build_initial_state(
        task=task,
        approval_status="approved",
        repo_path=repo_path,
        provider_name=provider_name,
        approval_note=approval_note,
    )

    return run_workflow(state=state, settings=settings)


def render_sidebar(settings: Settings) -> None:
    """Render sidebar configuration controls.

    Args:
        settings: Application settings used to show local provider details.
    """
    with st.sidebar:
        st.header("Run settings")

        st.session_state.sidebar_repo_path = st.text_input(
            "Repo path",
            value=st.session_state.sidebar_repo_path,
            help="Target repository where code changes and tests should run.",
        )

        provider_options = ["codex", "local"]
        current_provider = st.session_state.sidebar_provider_name
        current_index = (
            provider_options.index(current_provider)
            if current_provider in provider_options
            else 0
        )

        st.session_state.sidebar_provider_name = st.selectbox(
            "Provider",
            options=provider_options,
            index=current_index,
            help="Default coding provider for the Developer Agent.",
        )

        # Keep the sidebar progress snapshot aligned with the currently selected
        # provider while no workflow is active yet.
        if st.session_state.sidebar_run_snapshot.get("status") == "idle":
            update_sidebar_run_snapshot(
                {
                    "provider_name": st.session_state.sidebar_provider_name,
                }
            )

        # Show provider-specific details to make local provider behavior clearer.
        if st.session_state.sidebar_provider_name == "local":
            st.info(
                "Local provider is active. "
                "This version returns implementation guidance but does not write files yet."
            )
            st.caption(f"Local model: {settings.local_model_name}")
            st.caption(f"Ollama URL: {settings.ollama_base_url}")
        else:
            st.caption("Codex provider is active.")

        st.session_state.sidebar_approval_note = st.text_input(
            "Approval note",
            value=st.session_state.sidebar_approval_note,
            help="Optional note stored with the approval request.",
        )

        if st.button("Clear chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.pending_request = None
            st.session_state.sidebar_run_snapshot = {
                "status": "idle",
                "provider_name": st.session_state.sidebar_provider_name,
                "model_status": {},
            }
            st.rerun()

        st.divider()
        render_sidebar_progress_panel(st.session_state.sidebar_run_snapshot)


def render_chat_history() -> None:
    """Render all chat messages stored in session state."""
    for index, message in enumerate(st.session_state.chat_history):
        render_chat_message(message=message, index=index)


def handle_new_task(task_text: str) -> None:
    """Handle a new user task from the chat input.

    Args:
        task_text: Raw task text entered by the user.
    """
    normalized_task = task_text.strip()
    if not normalized_task:
        return

    repo_path = st.session_state.sidebar_repo_path.strip() or "."
    provider_name = st.session_state.sidebar_provider_name.strip().lower()
    approval_note = st.session_state.sidebar_approval_note.strip()

    st.session_state.request_counter += 1
    request_id = f"request_{st.session_state.request_counter}"

    add_user_message(normalized_task)

    with st.spinner("Creating plan..."):
        update_sidebar_run_snapshot(
            {
                "status": "planning",
                "provider_name": provider_name,
                "model_status": {},
            }
        )
        plan_preview = build_plan_preview(
            task=normalized_task,
            repo_path=repo_path,
            provider_name=provider_name,
            approval_note=approval_note,
        )

    update_sidebar_run_snapshot(
        {
            "status": plan_preview.get("status", "waiting_for_action"),
            "provider_name": provider_name,
            "model_status": {},
        }
    )

    add_assistant_message(
        content="I created a plan for your request. Please review it before moving to Act.",
        kind="plan",
        data=plan_preview,
    )

    st.session_state.pending_request = {
        "request_id": request_id,
        "stage": "plan",
        "task": normalized_task,
        "repo_path": repo_path,
        "provider_name": provider_name,
        "approval_note": approval_note,
        "plan_preview": plan_preview,
        "act_preview": None,
    }


def handle_pending_action(action: str) -> None:
    """Handle Plan / Act decision for the current pending request.

    Args:
        action: One of:
            - act
            - confirm
            - back
            - rejected
            - cancelled
    """
    pending_request = st.session_state.pending_request
    if not pending_request:
        return

    request_stage = pending_request.get("stage", "plan")
    task = pending_request["task"]
    repo_path = pending_request["repo_path"]
    provider_name = pending_request["provider_name"]
    approval_note = pending_request["approval_note"]
    plan_preview = pending_request.get("plan_preview") or {}
    act_preview = pending_request.get("act_preview") or {}

    # ---------------------------------------------------------------------
    # Stage 1: Plan
    # ---------------------------------------------------------------------
    if request_stage == "plan":
        if action == "act":
            preview = build_act_preview(
                task=task,
                repo_path=repo_path,
                provider_name=provider_name,
                approval_note=approval_note,
                plan_preview=plan_preview,
            )

            add_assistant_message(
                "Here is the Act preview. Review the planned file changes before execution.",
                kind="act_preview",
                data=preview,
            )

            update_sidebar_run_snapshot(
                {
                    "status": preview.get("status", "act_preview_ready"),
                    "provider_name": provider_name,
                    "model_status": {},
                }
            )

            pending_request["stage"] = "act_preview"
            pending_request["act_preview"] = preview
            st.session_state.pending_request = pending_request
            st.rerun()

        if action == "rejected":
            add_assistant_message("Request rejected. No code changes were made.")
            update_sidebar_run_snapshot(
                {
                    "status": "rejected",
                    "provider_name": provider_name,
                    "model_status": {},
                }
            )
            clear_pending_request()
            st.rerun()

        if action == "cancelled":
            add_assistant_message("Request cancelled. Nothing was executed.")
            update_sidebar_run_snapshot(
                {
                    "status": "cancelled",
                    "provider_name": provider_name,
                    "model_status": {},
                }
            )
            clear_pending_request()
            st.rerun()

    # ---------------------------------------------------------------------
    # Stage 2: Act preview
    # ---------------------------------------------------------------------
    if request_stage == "act_preview":
        if action == "back":
            add_assistant_message("Back to the plan. Review it again before moving to Act.")
            update_sidebar_run_snapshot(
                {
                    "status": "waiting_for_action",
                    "provider_name": provider_name,
                    "model_status": {},
                }
            )
            pending_request["stage"] = "plan"
            st.session_state.pending_request = pending_request
            st.rerun()

        if action == "cancelled":
            add_assistant_message("Request cancelled. Nothing was executed.")
            update_sidebar_run_snapshot(
                {
                    "status": "cancelled",
                    "provider_name": provider_name,
                    "model_status": {},
                }
            )
            clear_pending_request()
            st.rerun()

        if action == "confirm":
            progress_data = build_progress_snapshot(
                task=task,
                repo_path=repo_path,
                provider_name=provider_name,
                total_steps=int(plan_preview.get("total_steps", 0) or 0),
            )

            add_assistant_message(
                "Execution started. Progress will be shown below.",
                kind="progress",
                data=progress_data,
            )

            update_sidebar_run_snapshot(
                {
                    "status": "developing",
                    "provider_name": provider_name,
                }
            )

            with st.spinner("Running confirmed workflow..."):
                result = execute_approved_workflow(
                    task=task,
                    repo_path=repo_path,
                    provider_name=provider_name,
                    approval_note=approval_note,
                )

            development_result = result.get("development_result", {}) or {}
            model_status = development_result.get("model_status", {}) or {}

            update_sidebar_run_snapshot(
                {
                    "status": result.get("status", "finished"),
                    "provider_name": result.get("provider_name", provider_name),
                    "model_status": model_status,
                }
            )

            if provider_name == "local":
                add_assistant_message(
                    "Local provider finished. This run produced coding guidance and model output. "
                    "Direct file changes are not implemented for the local provider yet."
                )

            add_assistant_message(
                content=f"Workflow finished with status: {result.get('status', 'unknown')}.",
                kind="result",
                data=result,
            )

            clear_pending_request()
            st.rerun()


def main() -> None:
    """Run the chat-style Streamlit UI."""
    st.set_page_config(
        page_title="AI Dev Squad",
        page_icon="🤖",
        layout="wide",
    )

    initialize_session_state()
    settings = get_settings()
    render_sidebar(settings)

    st.title("AI Dev Squad")
    st.caption("Human-in-the-Loop AI coding workflow")

    st.markdown(
        """
Use this chat to ask for code changes or updates.

How it works:
1. You ask for a change
2. The Orchestrator creates a plan
3. You move from Plan to Act
4. You confirm changes
5. The workflow runs and returns the result
"""
    )

    render_chat_history()

    pending_request = st.session_state.pending_request
    if pending_request:
        request_stage = pending_request.get("stage", "plan")

        if request_stage == "plan":
            action = render_plan_action_bar(request_id=pending_request["request_id"])
            if action:
                handle_pending_action(action)

        elif request_stage == "act_preview":
            action = render_confirm_action_bar(request_id=pending_request["request_id"])
            if action:
                handle_pending_action(action)

    prompt_disabled = pending_request is not None
    prompt_placeholder = (
        "Finish the pending Plan / Act flow first..."
        if prompt_disabled
        else "Ask AI Dev Squad to create or update something..."
    )

    user_prompt = st.chat_input(
        prompt_placeholder,
        disabled=prompt_disabled,
    )

    if user_prompt:
        handle_new_task(user_prompt)
        st.rerun()


if __name__ == "__main__":
    main()