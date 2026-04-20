"""Inactive Streamlit UI scaffold for AI Dev Squad.

This file is included now so the future UI structure is ready,
but it is not required for the current local workflow.
"""

from __future__ import annotations

import streamlit as st

from app.ui.components import render_header, render_placeholder_panel


def main() -> None:
    """Render a simple placeholder UI."""
    st.set_page_config(page_title="AI Dev Squad", layout="wide")
    render_header()
    render_placeholder_panel()


if __name__ == "__main__":
    main()
