"""Union-type structured output parsing for LLM responses.

Constrains LLM output to ``MappingRationale | InsufficientEvidence``
by parsing JSON responses and validating against Pydantic schemas.
Falls back to ``InsufficientEvidence`` on invalid or non-JSON output.

Ref: GitHub Issue #19.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from ctrlmap.llm.client import OllamaClient
from ctrlmap.models.schemas import InsufficientEvidence, MappingRationale

_MAX_RETRIES = 2


def generate_rationale(
    *,
    control_text: str,
    chunk_text: str,
    model: str = "llama3",
    client: OllamaClient | None = None,
) -> MappingRationale | InsufficientEvidence:
    """Generate a structured rationale from the LLM.

    Sends the control + chunk to Ollama and parses the response into
    either ``MappingRationale`` or ``InsufficientEvidence``. Falls back
    to ``InsufficientEvidence`` if the LLM output is invalid.

    Args:
        control_text: The security control description.
        chunk_text: The policy text excerpt.
        model: Ollama model name (default: ``llama3``).
        client: Optional pre-configured OllamaClient.

    Returns:
        A ``MappingRationale`` or ``InsufficientEvidence`` instance.
    """
    if client is None:
        client = OllamaClient(model=model)

    for _attempt in range(_MAX_RETRIES + 1):
        raw = client.generate(control_text=control_text, chunk_text=chunk_text)
        result = _parse_response(raw)
        if result is not None:
            return result

    return InsufficientEvidence(
        reason="Invalid LLM output after retries.",
        required_context="A well-formed JSON response from the LLM.",
    )


def _extract_json(raw: str) -> str:
    """Extract a JSON object from raw LLM output.

    Handles common quirks: markdown code fences, preamble text,
    and trailing explanations surrounding the JSON.
    """
    text = raw.strip()

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    # Try to extract the first top-level JSON object { ... }
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)

    return text


def _parse_response(raw: str) -> MappingRationale | InsufficientEvidence | None:
    """Attempt to parse a raw LLM response into a structured output.

    Args:
        raw: The raw string response from the LLM.

    Returns:
        A validated Pydantic model instance, or None if parsing fails.
    """
    cleaned = _extract_json(raw)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        # Return None so the retry loop can re-ask the LLM
        return None

    output_type = data.get("type", "")

    try:
        if output_type == "MappingRationale":
            return MappingRationale(
                is_compliant=data["is_compliant"],
                confidence_score=data["confidence_score"],
                explanation=data["explanation"],
            )
        elif output_type == "InsufficientEvidence":
            return InsufficientEvidence(
                reason=data["reason"],
                required_context=data["required_context"],
            )
        else:
            return InsufficientEvidence(
                reason="Invalid LLM output: unknown response type.",
                required_context="Response must be MappingRationale or InsufficientEvidence.",
            )
    except (KeyError, ValidationError):
        return None
