"""Shared JSON extraction utilities for LLM response parsing.

Consolidates the JSON-from-raw-text extraction logic that was previously
duplicated across ``client.py``, ``structured_output.py``, and
``llm_chunker.py``.
"""

from __future__ import annotations

import json
import re


def extract_json_object(raw: str) -> str:
    """Extract a JSON object ``{…}`` from raw LLM output.

    Handles markdown code fences, preamble text, and trailing
    explanations surrounding the JSON object.

    Args:
        raw: Raw LLM response string.

    Returns:
        The extracted JSON substring (still a string, not parsed).
    """
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return text


def extract_json_array(raw: str) -> list[dict[str, str]]:
    """Extract a JSON array ``[…]`` from raw LLM output.

    Strips markdown code fences, then attempts direct parsing.
    Falls back to locating the **last** top-level ``[…]`` block by
    scanning backwards from the final ``]`` — this correctly handles
    chain-of-thought reasoning that may contain brackets like
    ``[access control]`` before the actual JSON array.

    Args:
        raw: Raw LLM response string.

    Returns:
        A parsed list of dicts, or an empty list on failure.
    """
    cleaned = raw.strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1 :]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: find the last balanced [...] block by scanning backwards
    # from the final ']'.  This skips CoT brackets in reasoning text.
    end = cleaned.rfind("]")
    if end == -1:
        return []

    depth = 0
    start = -1
    for i in range(end, -1, -1):
        if cleaned[i] == "]":
            depth += 1
        elif cleaned[i] == "[":
            depth -= 1
            if depth == 0:
                start = i
                break

    if start != -1:
        try:
            result = json.loads(cleaned[start : end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return []
