"""Union-type structured output parsing for LLM responses.

Constrains LLM output to ``MappingRationale | InsufficientEvidence``
by parsing JSON responses and validating against Pydantic schemas.
Falls back to ``InsufficientEvidence`` on invalid or non-JSON output.

Ref: GitHub Issue #19.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from contextlib import suppress

from pydantic import ValidationError

from ctrlmap._defaults import DEFAULT_LLM_MODEL
from ctrlmap.llm._json_utils import extract_json_object
from ctrlmap.llm.client import OllamaClient
from ctrlmap.models.schemas import ComplianceLevel, InsufficientEvidence, MappingRationale

# Compliance level priority: lower value = lower compliance (conservative).
# Used for tie-breaking — ties prefer the lower compliance level.
_LEVEL_PRIORITY: dict[ComplianceLevel, int] = {
    ComplianceLevel.NON_COMPLIANT: 1,
    ComplianceLevel.PARTIALLY_COMPLIANT: 2,
    ComplianceLevel.FULLY_COMPLIANT: 3,
}


def select_best_rationale(
    rationales: list[MappingRationale],
) -> MappingRationale | None:
    """Select the best rationale using majority-vote aggregation.

    Uses plurality voting: the compliance level that appears most
    frequently among all chunk rationales wins.  On ties, the
    **lower** (more conservative) compliance level is preferred —
    for a compliance tool, false positives are more dangerous than
    false negatives.

    Within the winning level, the rationale with the highest
    confidence score is returned.

    Args:
        rationales: List of MappingRationale instances from individual
            chunk evaluations. May be empty.

    Returns:
        The best rationale, or ``None`` if the list is empty.
    """
    if not rationales:
        return None
    if len(rationales) == 1:
        return rationales[0]

    # Count votes per compliance level
    level_counts: Counter[ComplianceLevel] = Counter(r.compliance_level for r in rationales)

    # Find the winning level: most votes, then lowest priority (conservative)
    winning_level = min(
        level_counts,
        key=lambda lvl: (-level_counts[lvl], _LEVEL_PRIORITY.get(lvl, 0)),
    )

    # Among rationales with the winning level, pick highest confidence
    winners = [r for r in rationales if r.compliance_level == winning_level]
    return max(winners, key=lambda r: r.confidence_score)


def _normalize_req_text(text: str) -> str:
    """Normalize sub-requirement text for deduplication.

    Lowercases, strips leading/trailing whitespace, collapses internal
    whitespace, and removes trailing punctuation. This prevents
    near-duplicate sub-requirements from inflating coverage counts.
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(".;,")
    return text


def aggregate_rationales(
    *,
    rationales: list[MappingRationale],
    sub_requirements: list[list[dict[str, object]]],
) -> MappingRationale | None:
    """Aggregate sub-requirement coverage across multiple chunk rationales.

    When multiple chunks each cover different sub-requirements, the
    combined coverage may upgrade a control from ``partially_compliant``
    to ``fully_compliant``. This function merges sub-requirement coverage
    from all chunks and recomputes the compliance level.

    Builds the canonical sub-requirement list from the **union** of all
    chunks' sub-requirements, not just the first chunk. This ensures
    sub-requirements mentioned only by later chunks are not silently
    ignored. Sub-requirement text is normalized before merging to
    prevent near-duplicates from inflating coverage counts.

    Falls back to :func:`select_best_rationale` when no sub-requirement
    data is available.

    Args:
        rationales: Rationale instances from per-chunk evaluations.
        sub_requirements: Parallel list of sub_requirements arrays from
            the LLM's batch response. May be shorter than rationales
            (missing entries are ignored).

    Returns:
        The aggregated rationale, or ``None`` if rationales is empty.
    """
    if not rationales:
        return None

    # Filter to sub_requirements that are non-empty lists
    valid_subs = [s for s in sub_requirements if isinstance(s, list) and s]

    if not valid_subs:
        return select_best_rationale(rationales)

    # Build a merged coverage map from the UNION of all chunks' sub-reqs.
    # Normalized text is used as the key to prevent near-duplicate inflation.
    # Maps: normalized_text → (original_text, covered)
    merged: dict[str, tuple[str, bool]] = {}
    for sub_list in valid_subs:
        for sub in sub_list:
            raw_text = str(sub.get("requirement", ""))
            norm = _normalize_req_text(raw_text)
            if not norm:
                continue
            if norm not in merged:
                merged[norm] = (raw_text, False)
            if sub.get("covered") is True:
                merged[norm] = (merged[norm][0], True)

    # Recompute compliance level from merged coverage
    covered = sum(1 for _, is_covered in merged.values() if is_covered)
    total = len(merged)

    if total == 0:
        return select_best_rationale(rationales)

    if covered == total:
        computed = ComplianceLevel.FULLY_COMPLIANT
    elif covered > 0:
        computed = ComplianceLevel.PARTIALLY_COMPLIANT
    else:
        computed = ComplianceLevel.NON_COMPLIANT

    # Get the best single rationale as a starting point for the explanation
    best = select_best_rationale(rationales)
    if best is None:
        return None

    # If aggregation changes the compliance level, update the rationale
    best_priority = _LEVEL_PRIORITY.get(best.compliance_level, 0)
    computed_priority = _LEVEL_PRIORITY.get(computed, 0)

    if computed_priority != best_priority:
        covered_reqs = [orig for orig, is_covered in merged.values() if is_covered]
        if computed_priority > best_priority:
            explanation = (
                f"Combined evidence from {len(valid_subs)} chunks covers all "
                f"{total} sub-requirements: {'; '.join(covered_reqs)}"
            )
        else:
            missing_reqs = [orig for orig, is_covered in merged.values() if not is_covered]
            explanation = (
                f"Combined evidence from {len(valid_subs)} chunks covers "
                f"{covered}/{total} sub-requirements. "
                f"Missing: {'; '.join(missing_reqs)}"
            )
        return _apply_confidence_floor(
            MappingRationale(
                is_compliant=computed != ComplianceLevel.NON_COMPLIANT,
                compliance_level=computed,
                confidence_score=min(best.confidence_score, 1.0),
                explanation=explanation,
            )
        )

    return _apply_confidence_floor(best)


# Confidence threshold: FC classifications below this score are
# downgraded to PC because the model is uncertain about full coverage.
_FC_CONFIDENCE_FLOOR = 0.7


def _apply_confidence_floor(rationale: MappingRationale) -> MappingRationale:
    """Downgrade fully_compliant → partially_compliant when confidence is low.

    A model that says "FC" at low confidence is often wrong about full
    sub-requirement coverage. This guard prevents false positives.
    """
    if (
        rationale.compliance_level == ComplianceLevel.FULLY_COMPLIANT
        and rationale.confidence_score < _FC_CONFIDENCE_FLOOR
    ):
        return MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
            confidence_score=rationale.confidence_score,
            explanation=rationale.explanation,
        )
    return rationale


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

            # Confidence floor: downgrade FC → PC when confidence is low.
            rationale = _apply_confidence_floor(rationale)

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


def extract_sub_requirements_from_batch(
    raw: str,
    *,
    expected_count: int,
) -> list[list[dict[str, object]]]:
    """Extract sub_requirements arrays from a raw LLM batch response.

    Parses the same JSON array as :func:`_parse_batch_response` but
    extracts only the ``sub_requirements`` field from each element.
    Returns a parallel list of sub_requirements arrays (one per chunk).

    Args:
        raw: The raw LLM response string.
        expected_count: Expected number of chunks.

    Returns:
        A list of sub_requirements arrays. Missing or invalid entries
        are returned as empty lists.
    """
    cleaned = raw.strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end < 0 or end <= start:
        return [[] for _ in range(expected_count)]

    try:
        items = json.loads(cleaned[start : end + 1])
    except (json.JSONDecodeError, TypeError):
        return [[] for _ in range(expected_count)]

    if not isinstance(items, list):
        return [[] for _ in range(expected_count)]

    result: list[list[dict[str, object]]] = []
    for item in items:
        if isinstance(item, dict):
            subs = item.get("sub_requirements", [])
            result.append(subs if isinstance(subs, list) else [])
        else:
            result.append([])

    # Pad to expected_count
    while len(result) < expected_count:
        result.append([])

    return result[:expected_count]
