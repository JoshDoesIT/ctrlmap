"""Union-type structured output parsing for LLM responses.

Constrains LLM output to ``MappingRationale | InsufficientEvidence``
by parsing JSON responses and validating against Pydantic schemas.
Falls back to ``InsufficientEvidence`` on invalid or non-JSON output.

Ref: GitHub Issue #19.
"""

from __future__ import annotations

import json
import re
from contextlib import suppress

from pydantic import ValidationError

from ctrlmap.llm.client import OllamaClient
from ctrlmap.models.schemas import ComplianceLevel, InsufficientEvidence, MappingRationale

# Compliance level priority for select_best_rationale (higher = better)
_LEVEL_PRIORITY: dict[ComplianceLevel, int] = {
    ComplianceLevel.FULLY_COMPLIANT: 3,
    ComplianceLevel.PARTIALLY_COMPLIANT: 2,
    ComplianceLevel.NON_COMPLIANT: 1,
}


def select_best_rationale(
    rationales: list[MappingRationale],
) -> MappingRationale | None:
    """Select the best rationale from multiple per-chunk evaluations.

    Ranking priority:
    1. Compliance level: ``fully_compliant`` > ``partially_compliant`` > ``non_compliant``
    2. Confidence score (higher is better)

    Args:
        rationales: List of MappingRationale instances from individual
            chunk evaluations. May be empty.

    Returns:
        The best rationale, or ``None`` if the list is empty.
    """
    if not rationales:
        return None

    return max(
        rationales,
        key=lambda r: (
            _LEVEL_PRIORITY.get(r.compliance_level, 0),
            r.confidence_score,
        ),
    )


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


def generate_gap_rationale(
    *,
    control_text: str,
    model: str = "llama3",
    client: OllamaClient | None = None,
) -> MappingRationale | InsufficientEvidence:
    """Generate a rationale for a control with no matching policy evidence.

    Sends the control to the LLM with a gap-focused prompt that asks it
    to explain why the control is non-compliant and what would be needed.

    Args:
        control_text: The security control description.
        model: Ollama model name (default: ``llama3``).
        client: Optional pre-configured OllamaClient.

    Returns:
        A ``MappingRationale`` or ``InsufficientEvidence`` instance.
    """
    if client is None:
        client = OllamaClient(model=model)

    for _attempt in range(_MAX_RETRIES + 1):
        raw = client.generate_gap(control_text=control_text)
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
            kwargs: dict[str, object] = {
                "is_compliant": data["is_compliant"],
                "confidence_score": data["confidence_score"],
                "explanation": data["explanation"],
            }
            # compliance_level is optional for backward compat
            if "compliance_level" in data:
                from ctrlmap.models.schemas import ComplianceLevel

                with suppress(ValueError):
                    kwargs["compliance_level"] = ComplianceLevel(data["compliance_level"])
            return MappingRationale(**kwargs)  # type: ignore[arg-type]
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
