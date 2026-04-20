"""Reusable Streamlit UI components for AI Dev Squad."""

from __future__ import annotations

import streamlit as st


def render_header() -> None:
    """Render the page title and summary."""
    st.title("AI Dev Squad")
    st.caption("Local-first Human-in-the-Loop AI coding MVP")


def render_placeholder_panel() -> None:
    """Render a placeholder panel for the future UI."""
    st.info(
        "The Streamlit UI is included in the project, but it is not active yet. "
        "Use it later for chat, approvals, and result display."
    )
