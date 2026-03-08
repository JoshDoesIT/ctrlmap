"""Shared formatting utilities for ctrlmap export formatters.

Centralizes text-formatting helpers that are used across multiple
export modules (HTML, Markdown, etc.).
"""

from __future__ import annotations


def truncate(text: str, max_len: int = 150) -> str:
    """Truncate text to *max_len* characters, adding ellipsis if needed.

    Newlines are collapsed to single spaces before truncation so that
    multi-line text renders cleanly in table cells and card previews.

    Args:
        text: The input text to truncate.
        max_len: Maximum character length (default: 150).

    Returns:
        The (possibly truncated) text string.
    """
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
