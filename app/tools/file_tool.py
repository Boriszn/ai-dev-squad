"""Simple file helper functions for AI Dev Squad.

These helpers are not heavily used in the MVP yet, but they provide a
clean place for future local file operations outside the coding provider.
"""

from __future__ import annotations

from pathlib import Path


def write_text_file(path: str, content: str) -> None:
    """Write text content to a file.

    Args:
        path: Target file path.
        content: File content.
    """
    Path(path).write_text(content, encoding="utf-8")


def read_text_file(path: str) -> str:
    """Read text content from a file.

    Args:
        path: Source file path.
    """
    return Path(path).read_text(encoding="utf-8")
