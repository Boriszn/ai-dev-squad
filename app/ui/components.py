"""Chat-style UI components for AI Dev Squad.

This module contains small Streamlit rendering helpers used by the
main chat-based Streamlit app. Keeping rendering logic here makes the
main UI file easier to read and maintain.

Design goals:
- simple chat-style layout
- reusable rendering helpers
- safe handling of missing workflow fields
- clear display of plan, messages, development, and test results
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def map_status_to_progress(status: str) -> tuple[float, str]:
    """Map workflow status to sidebar progress value and label.

    Progress model uses these steps:
    - Planning
    - Waiting for approval
    - Developing
    - Testing
    - Finished

    Args:
        status: Current workflow status string.

    Returns:
        Tuple of (progress_ratio, label).
    """
    normalized = (status or "").strip().lower()

    if not normalized or normalized == "idle":
        return (0.0, "Idle (no run yet)")

    if normalized in {"planning"}:
        return (0.2, "Planning")

    if normalized in {"waiting_for_approval", "pending"}:
        return (0.4, "Waiting for approval")

    if normalized in {"approved", "developing"}:
        return (0.6, "Developing")

    if normalized in {"developed", "testing", "tested"}:
        return (0.8, "Testing")

    if normalized == "finished":
        return (1.0, "Finished")

    if normalized in {"rejected", "cancelled"}:
        return (0.4, f"Stopped: {normalized}")

    if normalized in {"development_failed", "test_failed", "failed", "timeout"}:
        return (0.8, f"Stopped: {normalized}")

    return (0.0, f"Status: {normalized}")


def render_sidebar_progress_panel(run_snapshot: dict[str, Any]) -> None:
    """Render workflow progress and run usage details in sidebar.

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
        st.write(f"Tokens used in this run: {tokens_used}")
    else:
        st.write("Tokens used: not available")

    provider_name = str(model_status.get("provider") or run_snapshot.get("provider_name") or "unknown")
    provider_backend = str(model_status.get("provider_backend") or "not available")
    model_name = str(model_status.get("model") or "not available")

    st.subheader("Provider / model status")
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

        if kind == "result":
            render_result_message(message=message, index=index)
            return

        # Fallback for generic assistant/system-style text messages.
        st.markdown(message.get("content", ""))


def render_plan_message(message: dict[str, Any], index: int) -> None:
    """Render an assistant plan message.

    Args:
        message: Assistant message containing planning data.
        index: Numeric index used to build stable Streamlit keys.
    """
    data = message.get("data", {})

    st.markdown("### Proposed plan")
    st.markdown(message.get("content", "The Orchestrator prepared a plan."))

    task = data.get("task", "")
    if task:
        st.markdown(f"**Task**: {task}")

    plan = data.get("plan", "")
    if plan:
        st.info(plan)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", str(data.get("status", "unknown")))
    with col2:
        st.metric("Approval", str(data.get("approval_status", "unknown")))
    with col3:
        st.metric("Provider", str(data.get("provider_name", "unknown")))

    repo_path = data.get("repo_path", "")
    if repo_path:
        st.caption(f"Repo path: {repo_path}")

    messages = data.get("messages", [])
    if messages:
        with st.expander("Plan messages", expanded=False):
            for item_number, item in enumerate(messages, start=1):
                st.write(f"{item_number}. {item}")


def render_result_message(message: dict[str, Any], index: int) -> None:
    """Render an assistant workflow result message.

    Args:
        message: Assistant message containing workflow result data.
        index: Numeric index used to build stable Streamlit keys.
    """
    data = message.get("data", {})

    st.markdown(message.get("content", "Workflow result"))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", str(data.get("status", "unknown")))
    with col2:
        st.metric("Approval", str(data.get("approval_status", "unknown")))
    with col3:
        st.metric("Provider", str(data.get("provider_name", "unknown")))

    repo_path = data.get("repo_path", "")
    if repo_path:
        st.caption(f"Repo path: {repo_path}")

    plan = data.get("plan", "")
    if plan:
        with st.expander("Plan", expanded=False):
            st.info(plan)

    messages = data.get("messages", [])
    if messages:
        with st.expander("Workflow messages", expanded=True):
            for item_number, item in enumerate(messages, start=1):
                st.write(f"{item_number}. {item}")

    render_development_result(data=data, index=index)
    render_test_result(data=data, index=index)

    error_message = data.get("error_message", "")
    if error_message:
        with st.expander("Error", expanded=True):
            st.error(error_message)

    with st.expander("Raw result", expanded=False):
        st.json(data)


def render_development_result(data: dict[str, Any], index: int) -> None:
    """Render development result details.

    Args:
        data: Workflow result dictionary.
        index: Numeric index used to build stable Streamlit keys.
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

    model_status = development_result.get("model_status")
    if model_status:
        with st.expander("Model status", expanded=False):
            st.json(model_status)

    stdout_text = development_result.get("stdout", "")
    stderr_text = development_result.get("stderr", "")

    with st.expander("Developer stdout", expanded=False):
        st.code(stdout_text or "No stdout output.", language="text")

    with st.expander("Developer stderr", expanded=False):
        st.code(stderr_text or "No stderr output.", language="text")


def render_test_result(data: dict[str, Any], index: int) -> None:
    """Render test result details.

    Args:
        data: Workflow result dictionary.
        index: Numeric index used to build stable Streamlit keys.
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
        st.markdown(f"**Command**: `{command}`")

    stdout_text = test_result.get("stdout", "")
    stderr_text = test_result.get("stderr", "")

    with st.expander("Test stdout", expanded=False):
        st.code(stdout_text or "No stdout output.", language="text")

    with st.expander("Test stderr", expanded=False):
        st.code(stderr_text or "No stderr output.", language="text")


def render_pending_action_bar(request_id: str) -> str | None:
    """Render approval decision buttons for the current pending request.

    Args:
        request_id: Stable ID used to build unique Streamlit button keys.

    Returns:
        One of:
        - "approved"
        - "rejected"
        - "cancelled"
        - None
    """
    with st.chat_message("assistant"):
        st.markdown("### Waiting for your decision")
        st.write("Review the plan above, then choose what to do next.")

        col1, col2, col3 = st.columns(3)

        approve_clicked = col1.button(
            "Approve",
            key=f"approve_{request_id}",
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

    if approve_clicked:
        return "approved"
    if reject_clicked:
        return "rejected"
    if cancel_clicked:
        return "cancelled"

    return None