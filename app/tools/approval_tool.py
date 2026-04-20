"""Approval helper tool for AI Dev Squad.

The current MVP keeps approval in state, but this helper gives us
a small reusable place for approval-related logic.
"""

from __future__ import annotations


def is_approved(approval_status: str) -> bool:
    """Return True when the workflow has explicit approval."""
    return approval_status.lower().strip() == "approved"
