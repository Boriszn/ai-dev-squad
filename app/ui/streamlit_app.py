"""Chat-style Streamlit UI for AI Dev Squad.

This module provides a chat-like local control panel for running the
AI Dev Squad workflow without using LangGraph Studio.

Current goals:
- accept a user task through chat input
- generate a structured plan first
- keep chat enabled while the user refines the plan
- answer simple plan-discussion questions from the current plan state
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
The local provider is still generation-only for execution.
It can now become more stable during plan refinements by reusing:
- the original request
- the latest accepted plan snapshot
- additional user refinements
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
from app.models.codex_provider import CodexProvider
from app.models.local_provider import LocalProvider
from app.models.model_router import ModelRouter
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


def upsert_assistant_message(
    content: str,
    kind: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Replace the latest assistant message of the same kind, or append it.

    This keeps the UI cleaner by making the current plan and current
    Act Preview behave like living cards instead of piling up duplicate
    messages after every refinement.

    Args:
        content: Assistant message text.
        kind: Message kind such as plan or act_preview.
        data: Optional structured payload.
    """
    for index in range(len(st.session_state.chat_history) - 1, -1, -1):
        item = st.session_state.chat_history[index]
        if item.get("role") == "assistant" and item.get("kind") == kind:
            st.session_state.chat_history[index] = {
                "role": "assistant",
                "kind": kind,
                "content": content,
                "data": data or {},
            }
            return

    add_assistant_message(content=content, kind=kind, data=data)


def clear_pending_request() -> None:
    """Clear the current pending request from session state."""
    st.session_state.pending_request = None


def build_model_router(settings: Settings) -> ModelRouter:
    """Build the model router used by the UI planning path.

    Args:
        settings: Application settings.

    Returns:
        Configured model router.
    """
    return ModelRouter(
        providers={
            "codex": CodexProvider(settings=settings),
            "local": LocalProvider(settings=settings),
        },
        default_provider_name=settings.default_model_provider,
    )


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
    settings = get_settings()
    model_router = build_model_router(settings=settings)
    orchestrator = OrchestratorAgent(model_router=model_router)

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

    This is a lightweight fallback helper for providers that did not
    return reliable file predictions.

    Args:
        task: User task text.

    Returns:
        A dictionary with "create" and "update" file lists.
    """
    task_lower = task.lower()

    create_files: list[str] = []
    update_files: list[str] = []

    if any(
        keyword in task_lower
        for keyword in ["endpoint", "api", "/health", "route", "fastapi", "flask"]
    ):
        update_files.append("app.py")
        create_files.append("tests/test_health.py")

    if any(keyword in task_lower for keyword in ["readme", "docs", "documentation", ".md"]):
        update_files.append("README.md")

    if (
        any(keyword in task_lower for keyword in ["test", "tests", "pytest"])
        and "tests/test_health.py" not in create_files
    ):
        create_files.append("tests/test_feature.py")

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

    This uses file predictions from the current plan when available.
    For Codex and other providers, a simple fallback can still be used.
    For local provider, do not invent fallback file lists if the model
    did not return reliable predictions.

    Args:
        task: User task text.
        repo_path: Target repository path.
        provider_name: Selected provider name.
        approval_note: Optional approval note.
        plan_preview: Existing plan preview data.

    Returns:
        A structured act preview dictionary.
    """
    original_planned_file_changes = plan_preview.get("planned_file_changes") or {}
    create_files = original_planned_file_changes.get("create", []) or []
    update_files = original_planned_file_changes.get("update", []) or []

    used_heuristic_preview = False
    planned_file_changes = original_planned_file_changes

    if provider_name != "local" and not create_files and not update_files:
        planned_file_changes = infer_planned_file_changes(task)
        used_heuristic_preview = True

    messages = list(plan_preview.get("messages", []))
    messages.append("Act preview is ready.")
    messages.append("Review the planned file changes and confirm to continue.")

    notes = list(plan_preview.get("plan_notes", []))
    if used_heuristic_preview:
        notes.append("File preview is currently a UI fallback estimate.")
    elif provider_name == "local" and not create_files and not update_files:
        notes.append("Local provider did not return reliable file predictions yet.")

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


def append_refinement_to_task(existing_task: str, refinement_text: str) -> str:
    """Append a follow-up instruction to the current pending task.

    Args:
        existing_task: Current main task text.
        refinement_text: New follow-up user message.

    Returns:
        Combined task text used to rebuild the plan.
    """
    normalized_existing = existing_task.strip()
    normalized_refinement = refinement_text.strip()

    if not normalized_existing:
        return normalized_refinement

    if not normalized_refinement:
        return normalized_existing

    return (
        f"{normalized_existing}\n\n"
        f"Additional instruction:\n{normalized_refinement}"
    )


def build_effective_local_task(
    original_task: str,
    refinements: list[str],
    last_plan: dict[str, Any] | None,
) -> str:
    """Build a richer local-provider task from prior plan state.

    This is a lightweight quick fix before a real context/memory layer.
    It makes the next local planning call include:
    - the original request
    - the previous accepted plan
    - additional refinements

    Args:
        original_task: First user request.
        refinements: Later user corrections or additions.
        last_plan: Latest accepted plan snapshot, if available.

    Returns:
        Combined local planning prompt text.
    """
    sections = [f"Original request:\n{original_task.strip()}"]

    if last_plan:
        plan_summary = str(last_plan.get("plan_summary", "")).strip()
        plan_steps = last_plan.get("plan_steps", []) or []
        planned_file_changes = last_plan.get("planned_file_changes", {}) or {}
        create_files = planned_file_changes.get("create", []) or []
        update_files = planned_file_changes.get("update", []) or []

        previous_plan_lines: list[str] = []
        if plan_summary:
            previous_plan_lines.append(f"- Summary: {plan_summary}")

        if plan_steps:
            previous_plan_lines.append("- Steps:")
            for item in plan_steps:
                previous_plan_lines.append(f"  - {item}")

        if create_files:
            previous_plan_lines.append(f"- Files to create: {create_files}")

        if update_files:
            previous_plan_lines.append(f"- Files to update: {update_files}")

        if previous_plan_lines:
            sections.append(
                "Previous accepted plan:\n" + "\n".join(previous_plan_lines)
            )

    if refinements:
        refinement_lines = ["Additional refinements:"]
        for item in refinements:
            refinement_lines.append(f"- {item}")
        sections.append("\n".join(refinement_lines))

    sections.append(
        "Important rule:\n"
        "Preserve previous accepted decisions unless a newer refinement explicitly changes them."
    )

    return "\n\n".join(section for section in sections if section.strip())


def _get_active_plan_data(pending_request: dict[str, Any]) -> dict[str, Any]:
    """Return the most relevant plan-like data for the current stage.

    Args:
        pending_request: Current pending request object.

    Returns:
        Plan or act-preview data dictionary.
    """
    stage = pending_request.get("stage", "plan")

    if stage == "act_preview":
        return pending_request.get("act_preview") or pending_request.get("plan_preview") or {}

    return pending_request.get("plan_preview") or {}


def _extract_plan_file_lists(plan_data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Extract create/update file lists from plan data.

    Args:
        plan_data: Current plan or act-preview payload.

    Returns:
        Tuple of:
        - files to create
        - files to update
    """
    planned_file_changes = plan_data.get("planned_file_changes", {}) or {}
    create_files = planned_file_changes.get("create", []) or []
    update_files = planned_file_changes.get("update", []) or []
    return list(create_files), list(update_files)


def build_plan_discussion_answer(
    question_text: str,
    plan_data: dict[str, Any],
) -> str | None:
    """Answer simple plan-discussion questions from existing plan data.

    This avoids sending every small follow-up back to the model when the user
    is only asking about the current plan.

    Supported intent examples:
    - how many files
    - what files
    - summarize plan
    - give me detailed plan
    - list of files to update

    Args:
        question_text: New user message.
        plan_data: Current plan or act-preview payload.

    Returns:
        Assistant answer text, or None if the message should still be treated
        as a normal refinement.
    """
    normalized = " ".join(question_text.lower().split())

    create_files, update_files = _extract_plan_file_lists(plan_data)
    all_files = create_files + update_files
    unique_files = list(dict.fromkeys(all_files))

    if any(
        phrase in normalized
        for phrase in [
            "how many files",
            "how many file",
            "number of files",
            "how many files are you going to update",
            "how many files will you update",
        ]
    ):
        if not unique_files:
            return "Right now I do not have reliable file predictions yet."

        parts = [f"I currently plan to change {len(unique_files)} file(s)."]

        if create_files:
            parts.append(f"Create: {', '.join(create_files)}.")
        if update_files:
            parts.append(f"Update: {', '.join(update_files)}.")

        return " ".join(parts)

    if any(
        phrase in normalized
        for phrase in [
            "what files",
            "which files",
            "list files",
            "show files",
            "list of files",
            "files to update",
            "files you will update",
            "files are you going to update",
            "provide me with the list of files",
            "provide me with the list of files to update",
            "provide the list of files",
            "provide the list of files to update",
            "what are the files",
            "what file",
        ]
    ):
        if not unique_files:
            return "Right now I do not have reliable file predictions yet."

        lines = ["Current planned file changes:"]
        if create_files:
            lines.append(f"- Create: {', '.join(create_files)}")
        if update_files:
            lines.append(f"- Update: {', '.join(update_files)}")
        return "\n".join(lines)

    if any(
        phrase in normalized
        for phrase in [
            "summarize plan",
            "summary of the plan",
            "detailed plan",
            "plan details",
            "give me detailed plan",
            "what is the plan",
        ]
    ):
        plan_summary = str(plan_data.get("plan_summary", "")).strip()
        plan_steps = plan_data.get("plan_steps", []) or []

        lines: list[str] = []
        if plan_summary:
            lines.append(f"Plan summary: {plan_summary}")

        if plan_steps:
            lines.append("Implementation plan:")
            for index, step in enumerate(plan_steps, start=1):
                lines.append(f"{index}. {step}")

        if create_files or update_files:
            lines.append("Planned file changes:")
            if create_files:
                lines.append(f"- Create: {', '.join(create_files)}")
            if update_files:
                lines.append(f"- Update: {', '.join(update_files)}")

        if not lines:
            return "I do not have a detailed plan summary available yet."

        return "\n".join(lines)

    return None


def refresh_pending_request_from_refinement(refinement_text: str) -> None:
    """Treat a new chat message as a refinement of the current pending request.

    For local provider, this uses a lightweight baseline approach:
    - original request
    - previous accepted plan
    - latest refinements

    That makes refinements more stable without needing a full context layer.

    Args:
        refinement_text: New user instruction added during the current flow.
    """
    pending_request = st.session_state.pending_request
    if not pending_request:
        return

    request_stage = pending_request.get("stage", "plan")
    repo_path = pending_request["repo_path"]
    provider_name = pending_request["provider_name"]
    approval_note = pending_request["approval_note"]
    current_task = pending_request["task"]
    original_task = pending_request.get("original_task", current_task)
    refinements = list(pending_request.get("refinements", []))
    last_plan_snapshot = pending_request.get("last_plan_snapshot")

    add_user_message(refinement_text)

    active_plan_data = _get_active_plan_data(pending_request)
    plan_discussion_answer = build_plan_discussion_answer(
        question_text=refinement_text,
        plan_data=active_plan_data,
    )

    if plan_discussion_answer is not None:
        add_assistant_message(plan_discussion_answer)
        return

    if provider_name == "local":
        refinements.append(refinement_text)
        updated_task = build_effective_local_task(
            original_task=original_task,
            refinements=refinements,
            last_plan=last_plan_snapshot,
        )
    else:
        updated_task = append_refinement_to_task(
            existing_task=current_task,
            refinement_text=refinement_text,
        )

    with st.spinner("Updating plan..."):
        updated_plan_preview = build_plan_preview(
            task=updated_task,
            repo_path=repo_path,
            provider_name=provider_name,
            approval_note=approval_note,
        )

        updated_act_preview = None
        if request_stage == "act_preview":
            updated_act_preview = build_act_preview(
                task=updated_task,
                repo_path=repo_path,
                provider_name=provider_name,
                approval_note=approval_note,
                plan_preview=updated_plan_preview,
            )

    pending_request["task"] = updated_task
    pending_request["original_task"] = original_task
    pending_request["refinements"] = refinements
    pending_request["plan_preview"] = updated_plan_preview
    pending_request["last_plan_snapshot"] = updated_plan_preview
    pending_request["act_preview"] = updated_act_preview

    upsert_assistant_message(
        content="I updated the plan with your latest instruction.",
        kind="plan",
        data=updated_plan_preview,
    )

    if request_stage == "act_preview" and updated_act_preview:
        upsert_assistant_message(
            content="Here is the refreshed Act preview.",
            kind="act_preview",
            data=updated_act_preview,
        )
        update_sidebar_run_snapshot(
            {
                "status": updated_act_preview.get("status", "act_preview_ready"),
                "provider_name": provider_name,
                "model_status": {},
            }
        )
    else:
        update_sidebar_run_snapshot(
            {
                "status": updated_plan_preview.get("status", "waiting_for_action"),
                "provider_name": provider_name,
                "model_status": {},
            }
        )

    st.session_state.pending_request = pending_request


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

        if st.session_state.sidebar_run_snapshot.get("status") == "idle":
            update_sidebar_run_snapshot(
                {
                    "provider_name": st.session_state.sidebar_provider_name,
                }
            )

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


def start_new_pending_request(
    task_text: str,
    repo_path: str,
    provider_name: str,
    approval_note: str,
) -> None:
    """Start a brand new pending Plan / Act request.

    Args:
        task_text: First task message.
        repo_path: Target repository path.
        provider_name: Selected provider name.
        approval_note: Optional approval note.
    """
    st.session_state.request_counter += 1
    request_id = f"request_{st.session_state.request_counter}"

    add_user_message(task_text)

    effective_task = task_text
    if provider_name == "local":
        effective_task = build_effective_local_task(
            original_task=task_text,
            refinements=[],
            last_plan=None,
        )

    with st.spinner("Creating plan..."):
        update_sidebar_run_snapshot(
            {
                "status": "planning",
                "provider_name": provider_name,
                "model_status": {},
            }
        )
        plan_preview = build_plan_preview(
            task=effective_task,
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

    upsert_assistant_message(
        content="I created a plan for your request. Please review it before moving to Act.",
        kind="plan",
        data=plan_preview,
    )

    st.session_state.pending_request = {
        "request_id": request_id,
        "stage": "plan",
        "task": effective_task,
        "original_task": task_text,
        "refinements": [],
        "repo_path": repo_path,
        "provider_name": provider_name,
        "approval_note": approval_note,
        "plan_preview": plan_preview,
        "last_plan_snapshot": plan_preview,
        "act_preview": None,
    }


def handle_user_prompt(task_text: str) -> None:
    """Handle a new user prompt.

    Behavior:
    - no pending request -> start a new request
    - pending request in plan/act_preview -> refine the current request
    - pending request in running -> ignore, because input should be disabled

    Args:
        task_text: Raw user input from chat.
    """
    normalized_task = task_text.strip()
    if not normalized_task:
        return

    repo_path = st.session_state.sidebar_repo_path.strip() or "."
    provider_name = st.session_state.sidebar_provider_name.strip().lower()
    approval_note = st.session_state.sidebar_approval_note.strip()

    pending_request = st.session_state.pending_request
    if not pending_request:
        start_new_pending_request(
            task_text=normalized_task,
            repo_path=repo_path,
            provider_name=provider_name,
            approval_note=approval_note,
        )
        return

    request_stage = pending_request.get("stage", "plan")
    if request_stage in {"plan", "act_preview"}:
        refresh_pending_request_from_refinement(normalized_task)


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

            upsert_assistant_message(
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

            pending_request["stage"] = "running"
            st.session_state.pending_request = pending_request

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
3. You can refine the plan in chat
4. You move from Plan to Act
5. You confirm changes
6. The workflow runs and returns the result
"""
    )

    render_chat_history()

    pending_request = st.session_state.pending_request
    request_stage = pending_request.get("stage") if pending_request else None

    if pending_request:
        if request_stage == "plan":
            action = render_plan_action_bar(request_id=pending_request["request_id"])
            if action:
                handle_pending_action(action)

        elif request_stage == "act_preview":
            action = render_confirm_action_bar(request_id=pending_request["request_id"])
            if action:
                handle_pending_action(action)

    prompt_disabled = request_stage == "running"
    prompt_placeholder = (
        "Execution is running..."
        if prompt_disabled
        else "Ask AI Dev Squad to create or update something..."
    )

    user_prompt = st.chat_input(
        prompt_placeholder,
        disabled=prompt_disabled,
    )

    if user_prompt:
        handle_user_prompt(user_prompt)
        st.rerun()


if __name__ == "__main__":
    main()