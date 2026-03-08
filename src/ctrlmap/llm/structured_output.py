"""Union-type structured output parsing for LLM responses.

Constrains LLM output to ``MappingRationale | InsufficientEvidence``
by parsing JSON responses and validating against Pydantic schemas.
Falls back to ``InsufficientEvidence`` on invalid or non-JSON output.

Ref: GitHub Issue #19.
"""

from __future__ import annotations

import json
from contextlib import suppress

from pydantic import ValidationError

from ctrlmap._defaults import DEFAULT_LLM_MODEL
from ctrlmap.llm._json_utils import extract_json_object
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
    model: str = DEFAULT_LLM_MODEL,
    client: OllamaClient | None = None,
) -> MappingRationale | InsufficientEvidence:
    """Generate a structured rationale from the LLM.

    Sends the control + chunk to Ollama and parses the response into
    either ``MappingRationale`` or ``InsufficientEvidence``. Falls back
    to ``InsufficientEvidence`` if the LLM output is invalid.

    Args:
        control_text: The security control description.
        chunk_text: The policy text excerpt.
        model: Ollama model name (default: ``qwen2.5:14b``).
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
    model: str = DEFAULT_LLM_MODEL,
    client: OllamaClient | None = None,
) -> MappingRationale | InsufficientEvidence:
    """Generate a rationale for a control with no matching policy evidence.

    Sends the control to the LLM with a gap-focused prompt that asks it
    to explain why the control is non-compliant and what would be needed.

    Args:
        control_text: The security control description.
        model: Ollama model name (default: ``qwen2.5:14b``).
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


def _parse_response(raw: str) -> MappingRationale | InsufficientEvidence | None:
    """Attempt to parse a raw LLM response into a structured output.

    Args:
        raw: The raw string response from the LLM.

    Returns:
        A validated Pydantic model instance, or None if parsing fails.
    """
    cleaned = extract_json_object(raw)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        # Return None so the retry loop can re-ask the LLM
        return None

    output_type = data.get("type", "")

    try:
        if output_type == "MappingRationale":
            is_compliant = data["is_compliant"]
            confidence_score = data["confidence_score"]
            explanation = data["explanation"]
            compliance_level: ComplianceLevel | None = None

            # compliance_level is optional for backward compat
            if "compliance_level" in data:
                with suppress(ValueError):
                    compliance_level = ComplianceLevel(data["compliance_level"])

            # Programmatic override: if sub_requirements array is present,
            # verify compliance_level is consistent with the counts.
            sub_reqs = data.get("sub_requirements")
            if isinstance(sub_reqs, list) and sub_reqs:
                covered = sum(1 for s in sub_reqs if s.get("covered") is True)
                total = len(sub_reqs)
                if covered == total:
                    computed = ComplianceLevel.FULLY_COMPLIANT
                elif covered > 0:
                    computed = ComplianceLevel.PARTIALLY_COMPLIANT
                else:
                    computed = ComplianceLevel.NON_COMPLIANT
                compliance_level = computed
                is_compliant = computed != ComplianceLevel.NON_COMPLIANT

            rationale_kwargs: dict[str, object] = {
                "is_compliant": is_compliant,
                "confidence_score": confidence_score,
                "explanation": explanation,
            }
            if compliance_level is not None:
                rationale_kwargs["compliance_level"] = compliance_level

            rationale = MappingRationale.model_validate(rationale_kwargs)

            # Guard: zero confidence means the LLM found the chunk
            # irrelevant but used the wrong response type.  Convert to
            # InsufficientEvidence so downstream logic treats it correctly.
            if rationale.confidence_score == 0.0:
                return InsufficientEvidence(
                    reason=explanation or "Zero-confidence rationale.",
                    required_context="Policy text directly addressing the control.",
                )

            return rationale
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


def _parse_batch_response(
    raw: str,
    *,
    expected_count: int,
) -> list[MappingRationale | InsufficientEvidence] | None:
    """Parse a JSON array of batch evaluation results from the LLM.

    Each element in the array is parsed independently using
    ``_parse_response``. Elements that fail to parse are replaced with
    ``InsufficientEvidence``.

    Args:
        raw: The raw LLM response string, expected to contain a JSON array.
        expected_count: The number of chunks that were sent.

    Returns:
        A list of parsed results, or ``None`` if the response cannot be
        parsed as a JSON array at all.
    """

    # Try to extract a JSON array from the response
    cleaned = raw.strip()

    # Find the JSON array boundaries
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end < 0 or end <= start:
        return None

    try:
        items = json.loads(cleaned[start : end + 1])
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(items, list):
        return None

    results: list[MappingRationale | InsufficientEvidence] = []
    for item in items:
        if not isinstance(item, dict):
            results.append(
                InsufficientEvidence(
                    reason="Invalid batch element: not a JSON object.",
                    required_context="Each element must be a valid JSON object.",
                )
            )
            continue

        # Re-serialize and parse through the standard _parse_response
        item_json = json.dumps(item)
        parsed = _parse_response(item_json)
        if parsed is not None:
            results.append(parsed)
        else:
            results.append(
                InsufficientEvidence(
                    reason="Failed to parse batch element.",
                    required_context="A valid MappingRationale or InsufficientEvidence.",
                )
            )

    # Pad with InsufficientEvidence if fewer results than expected
    while len(results) < expected_count:
        results.append(
            InsufficientEvidence(
                reason="Missing batch element in LLM response.",
                required_context="One evaluation per chunk.",
            )
        )

    return results[:expected_count]
