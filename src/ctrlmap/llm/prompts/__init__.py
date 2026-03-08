"""Prompt template loader for LLM prompts.

Loads prompt templates from ``.txt`` files co-located in this package
directory.  Prompts are read once and cached for the lifetime of the
process.  Keeping prompts in plain-text files makes them easy to
review, diff, and iterate on independently of the Python code.
"""

from __future__ import annotations

import functools
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


@functools.cache
def load_prompt(name: str) -> str:
    """Load a prompt template by filename.

    Args:
        name: Filename (e.g. ``"compliance_rationale.txt"``).

    Returns:
        The raw template string with ``{placeholders}`` intact.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    path = _PROMPT_DIR / name
    return path.read_text(encoding="utf-8")
