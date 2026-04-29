"""Chat-style Streamlit UI for AI Dev Squad.

This module provides a chat-like local control panel for running the
AI Dev Squad workflow without using LangGraph Studio.

Current goals:
- accept a user task through chat input
- generate a plan first
- ask for human approval with buttons
- run the workflow only after approval
- show final result as assistant messages

Important note:
The current graph does not yet use a true interrupt/resume approval flow.
Because of that, this UI handles the approval interaction at the UI layer:
- first build the plan only
- then run the full workflow when the user clicks Approve
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
from app.config.settings import get_settings
from app.services.execution_service import run_workflow
from app.services.task_service import build_initial_state
from app.ui.components import (
    render_chat_message,
    render_pending_action_bar,
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
        kind: Message kind such as text, plan, or result.
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
    messages.append("Workflow is waiting for human approval.")
    messages.append("Use Approve, Reject, or Cancel to continue.")

    return {
        **state,
        **plan_result,
        "status": "waiting_for_approval",
        "approval_status": "pending",
        "approval_required": True,
        "messages": messages,
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


def render_sidebar() -> None:
    """Render sidebar configuration controls."""
    with st.sidebar:
        st.header("Run settings")

        st.session_state.sidebar_repo_path = st.text_input(
            "Repo path",
            value=st.session_state.sidebar_repo_path,
            help="Target repository where code changes and tests should run.",
        )

        provider_options = ["codex", "local"]
        current_provider = st.session_state.sidebar_provider_name
        current_index = provider_options.index(current_provider) if current_provider in provider_options else 0

        st.session_state.sidebar_provider_name = st.selectbox(
            "Provider",
            options=provider_options,
            index=current_index,
            help="Default coding provider for the Developer Agent.",
        )

        if st.session_state.sidebar_run_snapshot.get("status") == "idle":
            update_sidebar_run_snapshot(
                {
                    "provider_name": st.session_state.sidebar_provider_name,
                }
            )

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
            "status": plan_preview.get("status", "waiting_for_approval"),
            "provider_name": provider_name,
            "model_status": {},
        }
    )

    add_assistant_message(
        content="I created a plan for your request. Please review and confirm.",
        kind="plan",
        data=plan_preview,
    )

    st.session_state.pending_request = {
        "request_id": request_id,
        "task": normalized_task,
        "repo_path": repo_path,
        "provider_name": provider_name,
        "approval_note": approval_note,
        "plan_preview": plan_preview,
    }


def handle_pending_action(action: str) -> None:
    """Handle approval decision for the current pending request.

    Args:
        action: One of approved, rejected, or cancelled.
    """
    pending_request = st.session_state.pending_request
    if not pending_request:
        return

    task = pending_request["task"]
    repo_path = pending_request["repo_path"]
    provider_name = pending_request["provider_name"]
    approval_note = pending_request["approval_note"]

    if action == "approved":
        add_assistant_message("Approval received. Running developer and tester now.")
        update_sidebar_run_snapshot(
            {
                "status": "developing",
                "provider_name": provider_name,
            }
        )

        with st.spinner("Running approved workflow..."):
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

        add_assistant_message(
            content=f"Workflow finished with status: {result.get('status', 'unknown')}.",
            kind="result",
            data=result,
        )
        clear_pending_request()
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


def main() -> None:
    """Run the chat-style Streamlit UI."""
    st.set_page_config(
        page_title="AI Dev Squad",
        page_icon="🤖",
        layout="wide",
    )

    initialize_session_state()
    render_sidebar()

    st.title("AI Dev Squad")
    st.caption("Human-in-the-Loop AI coding workflow")

    st.markdown(
        """
Use this chat to ask for code changes or updates.

How it works:
1. You ask for a change
2. The Orchestrator creates a plan
3. You approve, reject, or cancel
4. After approval, the Developer and Tester run
"""
    )

    render_chat_history()

    pending_request = st.session_state.pending_request
    if pending_request:
        action = render_pending_action_bar(request_id=pending_request["request_id"])
        if action:
            handle_pending_action(action)

    prompt_disabled = pending_request is not None
    prompt_placeholder = (
        "Finish the pending approval first..."
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