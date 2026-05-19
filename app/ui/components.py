"""Chat-style UI components for AI Dev Squad.

This module contains Streamlit rendering helpers used by the main
chat-based Streamlit app.

Design goals:
- simple chat-style layout
- reusable rendering helpers
- safe handling of missing workflow fields
- compact display of plan, preview, progress, and final results
- lighter UI closer to the Cline-style flow
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def map_status_to_progress(status: str) -> tuple[float, str]:
    """Map workflow status to sidebar progress value and label.

    Args:
        status: Current workflow status string.

    Returns:
        Tuple of:
        - progress ratio between 0.0 and 1.0
        - short human-readable label
    """
    normalized = (status or "").strip().lower()

    if not normalized or normalized == "idle":
        return (0.0, "Idle")

    if normalized in {"created", "planned", "planning"}:
        return (0.2, "Planning")

    if normalized in {"waiting_for_approval", "waiting_for_action", "pending"}:
        return (0.4, "Waiting")

    if normalized in {"approved", "act_preview_ready", "developing"}:
        return (0.6, "Acting")

    if normalized in {"developed", "testing", "tested"}:
        return (0.8, "Testing")

    if normalized in {"finished", "completed"}:
        return (1.0, "Finished")

    if normalized in {"rejected", "cancelled"}:
        return (0.4, f"Stopped: {normalized}")

    if normalized in {"development_failed", "test_failed", "failed", "timeout"}:
        return (0.8, f"Stopped: {normalized}")

    return (0.0, normalized)


def render_sidebar_progress_panel(run_snapshot: dict[str, Any]) -> None:
    """Render workflow progress and run usage details in the sidebar.

    Args:
        run_snapshot: Latest run snapshot containing status and optional
            development/model metadata.
    """
    status = str(run_snapshot.get("status", "idle"))
    progress_ratio, progress_label = map_status_to_progress(status)

    st.subheader("Workflow progress")
    st.progress(progress_ratio)
    st.caption(progress_label)

    model_status = run_snapshot.get("model_status", {}) or {}
    tokens_used = model_status.get("tokens_used")

    st.subheader("Usage")
    if isinstance(tokens_used, int):
        st.write(f"Tokens used: {tokens_used}")
    else:
        st.write("Tokens used: not available")

    provider_name = str(
        model_status.get("provider")
        or run_snapshot.get("provider_name")
        or "unknown"
    )
    provider_backend = str(model_status.get("provider_backend") or "not available")
    model_name = str(model_status.get("model") or "not available")

    st.subheader("Provider / model")
    st.write(f"Provider: {provider_name}")
    st.write(f"Backend: {provider_backend}")
    st.write(f"Model: {model_name}")


def render_chat_message(message: dict[str, Any], index: int) -> None:
    """Render one chat message.

    Args:
        message: Chat message dictionary stored in session state.
        index: Numeric index used to build stable Streamlit keys.
    """
    role = message.get("role", "assistant")
    kind = message.get("kind", "text")

    with st.chat_message(role):
        if role == "user":
            st.markdown(message.get("content", ""))
            return

        if kind == "plan":
            render_plan_message(message=message, index=index)
            return

        if kind == "act_preview":
            render_act_preview_message(message=message, index=index)
            return

        if kind == "progress":
            render_progress_message(message=message, index=index)
            return

        if kind == "result":
            render_result_message(message=message, index=index)
            return

        st.markdown(message.get("content", ""))


def render_plan_message(message: dict[str, Any], index: int) -> None:
    """Render a compact Plan card.

    Args:
        message: Assistant message containing planning data.
        index: Numeric index used to build stable Streamlit keys.
    """
    del index  # kept for stable function signature

    data = message.get("data", {}) or {}

    st.markdown("## Plan Created")
    st.markdown(message.get("content", "The Orchestrator prepared a plan."))

    task = data.get("task", "")
    if task:
        st.markdown(f"**Task:** {task}")

    plan_summary = data.get("plan_summary", "")
    if plan_summary:
        st.info(plan_summary)

    plan_steps = data.get("plan_steps", []) or []
    if plan_steps:
        st.markdown("**Implementation plan**")
        for step_number, step in enumerate(plan_steps, start=1):
            st.write(f"{step_number}. {step}")

    plan_notes = data.get("plan_notes", []) or []
    if plan_notes:
        with st.expander("Notes", expanded=False):
            for note in plan_notes:
                st.write(f"- {note}")

    act_summary = data.get("act_summary", "")
    if act_summary:
        st.caption(f"Next step: {act_summary}")

    _render_status_line(data=data)


def render_act_preview_message(message: dict[str, Any], index: int) -> None:
    """Render a compact Act Preview card.

    Args:
        message: Assistant message containing act preview data.
        index: Numeric index used to build stable Streamlit keys.
    """
    del index  # kept for stable function signature

    data = message.get("data", {}) or {}

    st.markdown("## Act Preview")
    st.markdown(
        message.get(
            "content",
            "Review the planned file changes before execution starts.",
        )
    )

    act_summary = data.get("act_summary", "")
    if act_summary:
        st.info(act_summary)

    planned_file_changes = data.get("planned_file_changes", {}) or {}
    create_files = planned_file_changes.get("create", []) or []
    update_files = planned_file_changes.get("update", []) or []

    if create_files:
        st.markdown("**Files to create**")
        for item in create_files:
            st.write(f"- {item}")

    if update_files:
        st.markdown("**Files to update**")
        for item in update_files:
            st.write(f"- {item}")

    if not create_files and not update_files:
        st.caption("No planned file changes yet.")

    _render_status_line(data=data)


def render_progress_message(message: dict[str, Any], index: int) -> None:
    """Render a compact progress card.

    Args:
        message: Assistant message containing execution progress data.
        index: Numeric index used to build stable Streamlit keys.
    """
    del index  # kept for stable function signature

    data = message.get("data", {}) or {}

    st.markdown("## Progress")
    st.markdown(message.get("content", "Execution is running."))

    current_step = data.get("current_step", "")
    current_step_index = int(data.get("current_step_index", 0) or 0)
    total_steps = int(data.get("total_steps", 0) or 0)

    if total_steps > 0:
        progress_ratio = min(current_step_index / total_steps, 1.0)
        st.progress(progress_ratio)
        st.caption(f"Step {current_step_index} of {total_steps}")

    if current_step:
        st.write(f"**Current step:** {current_step}")

    step_results = data.get("step_results", []) or []
    if step_results:
        with st.expander("Step details", expanded=False):
            for item_number, item in enumerate(step_results, start=1):
                st.json({"step_number": item_number, **item})

    _render_status_line(data=data)


def render_result_message(message: dict[str, Any], index: int) -> None:
    """Render a compact Task Completed card.

    Args:
        message: Assistant message containing workflow result data.
        index: Numeric index used to build stable Streamlit keys.
    """
    del index  # kept for stable function signature

    data = message.get("data", {}) or {}

    st.markdown("## Task Completed")
    st.markdown(message.get("content", "Workflow result"))

    final_summary = data.get("final_summary", "")
    if final_summary:
        st.success(final_summary)

    _render_status_line(data=data)

    final_report = data.get("final_report", {}) or {}
    files_changed = final_report.get("files_changed", []) or []
    what_was_added = final_report.get("what_was_added", []) or []
    notes = final_report.get("notes", []) or []
    test_result_summary = final_report.get("test_result", "")

    if files_changed:
        st.markdown("**Files changed**")
        for item in files_changed:
            st.write(f"- {item}")

    if what_was_added:
        st.markdown("**What was added**")
        for item in what_was_added:
            st.write(f"- {item}")

    if test_result_summary:
        st.markdown(f"**Test result:** {test_result_summary}")

    if notes:
        with st.expander("Notes", expanded=False):
            for note in notes:
                st.write(f"- {note}")

    render_development_result(data=data)
    render_test_result(data=data)

    error_message = data.get("error_message", "")
    if error_message:
        with st.expander("Error", expanded=True):
            st.error(error_message)

    with st.expander("Raw result", expanded=False):
        st.json(data)


def render_development_result(data: dict[str, Any]) -> None:
    """Render development result details.

    Args:
        data: Workflow result dictionary.
    """
    development_result = data.get("development_result")
    if not development_result:
        return

    st.markdown("### Development result")

    success = development_result.get("success")
    summary = development_result.get("summary", "No development summary available.")

    if success is True:
        st.success(summary)
    elif success is False:
        st.error(summary)
    else:
        st.info(summary)

    stdout_text = development_result.get("stdout", "")
    stderr_text = development_result.get("stderr", "")

    with st.expander("Developer output", expanded=False):
        st.code(stdout_text or "No stdout output.", language="text")

    if stderr_text:
        with st.expander("Developer error output", expanded=False):
            st.code(stderr_text, language="text")

    model_status = development_result.get("model_status")
    if model_status:
        with st.expander("Model status", expanded=False):
            st.json(model_status)


def render_test_result(data: dict[str, Any]) -> None:
    """Render test result details.

    Args:
        data: Workflow result dictionary.
    """
    test_result = data.get("test_result")
    if not test_result:
        return

    st.markdown("### Test result")

    success = test_result.get("success")
    summary = test_result.get("summary", "No test summary available.")

    if success is True:
        st.success(summary)
    elif success is False:
        st.error(summary)
    else:
        st.info(summary)

    command = test_result.get("command", "")
    if command:
        st.caption(f"Command: {command}")

    stdout_text = test_result.get("stdout", "")
    stderr_text = test_result.get("stderr", "")

    with st.expander("Test output", expanded=False):
        st.code(stdout_text or "No stdout output.", language="text")

    if stderr_text:
        with st.expander("Test error output", expanded=False):
            st.code(stderr_text, language="text")


def render_plan_action_bar(request_id: str) -> str | None:
    """Render action buttons shown after the Plan card.

    Args:
        request_id: Stable ID used to build unique Streamlit button keys.

    Returns:
        One of:
        - "act"
        - "rejected"
        - "cancelled"
        - None
    """
    with st.chat_message("assistant"):
        col1, col2, col3 = st.columns(3)

        act_clicked = col1.button(
            "Act",
            key=f"act_{request_id}",
            type="primary",
            use_container_width=True,
        )
        reject_clicked = col2.button(
            "Reject",
            key=f"reject_{request_id}",
            use_container_width=True,
        )
        cancel_clicked = col3.button(
            "Cancel",
            key=f"cancel_{request_id}",
            use_container_width=True,
        )

    if act_clicked:
        return "act"
    if reject_clicked:
        return "rejected"
    if cancel_clicked:
        return "cancelled"

    return None


def render_confirm_action_bar(request_id: str) -> str | None:
    """Render action buttons shown after the Act Preview card.

    Args:
        request_id: Stable ID used to build unique Streamlit button keys.

    Returns:
        One of:
        - "confirm"
        - "back"
        - "cancelled"
        - None
    """
    with st.chat_message("assistant"):
        col1, col2, col3 = st.columns(3)

        confirm_clicked = col1.button(
            "Confirm",
            key=f"confirm_{request_id}",
            type="primary",
            use_container_width=True,
        )
        back_clicked = col2.button(
            "Back",
            key=f"back_{request_id}",
            use_container_width=True,
        )
        cancel_clicked = col3.button(
            "Cancel",
            key=f"cancel_confirm_{request_id}",
            use_container_width=True,
        )

    if confirm_clicked:
        return "confirm"
    if back_clicked:
        return "back"
    if cancel_clicked:
        return "cancelled"

    return None


def render_pending_action_bar(request_id: str) -> str | None:
    """Backward-compatible wrapper for the old plan action bar.

    Args:
        request_id: Stable ID used to build unique Streamlit button keys.

    Returns:
        Same output as render_plan_action_bar().
    """
    return render_plan_action_bar(request_id=request_id)


def _render_status_line(data: dict[str, Any]) -> None:
    """Render a small one-line status summary.

    Args:
        data: Workflow-related data dictionary.
    """
    status = str(data.get("status", "unknown"))
    approval = str(data.get("approval_status", "unknown"))
    provider = str(data.get("provider_name", "unknown"))
    repo_path = str(data.get("repo_path", ""))

    parts = [
        f"**Status:** {status}",
        f"**Approval:** {approval}",
        f"**Provider:** {provider}",
    ]

    if repo_path:
        parts.append(f"**Repo:** {repo_path}")

    st.caption(" | ".join(parts))