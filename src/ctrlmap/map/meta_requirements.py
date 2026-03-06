"""Meta-requirement detection and sibling aggregation.

Identifies governance/documentation requirements that refer to other
controls (e.g. "All security policies in Requirement X are documented")
using LLM classification, then infers their compliance by aggregating
the verdict of sibling controls in the same requirement family.
"""

from __future__ import annotations

from ctrlmap.llm.client import OllamaClient
from ctrlmap.models.schemas import MappedResult, MappingRationale, SecurityControl


def classify_meta_requirement(
    *,
    control: SecurityControl,
    client: OllamaClient,
) -> bool:
    """Classify whether a control is a meta-requirement via LLM.

    A meta-requirement is a governance/documentation requirement about
    other requirements (e.g. "All security policies for Requirement X
    are documented"). A substantive control is a specific technical or
    procedural requirement.

    Args:
        control: The SecurityControl to classify.
        client: Pre-configured OllamaClient instance.

    Returns:
        ``True`` if the control is a meta-requirement, ``False`` otherwise.
    """
    control_text = f"{control.control_id}: {control.title}. {control.description}"
    return client.classify_control_type(control_text=control_text)


def classify_meta_controls(
    *,
    results: list[MappedResult],
    client: OllamaClient,
) -> set[str]:
    """Identify which controls are meta-requirements.

    Classifies **all** controls via LLM — including those that already
    have rationales or supporting chunks.  Governance controls that
    happen to match a chunk still need to be resolved against their
    siblings.

    Args:
        results: List of MappedResult objects.
        client: Pre-configured OllamaClient instance.

    Returns:
        Set of control IDs that are meta-requirements.
    """
    meta_ids: set[str] = set()
    for result in results:
        if classify_meta_requirement(control=result.control, client=client):
            meta_ids.add(result.control.control_id)
    return meta_ids


def _get_requirement_family(control_id: str) -> str:
    """Extract the top-level requirement family from a control ID.

    Examples:
        ``"1.1.1"`` → ``"1"``
        ``"3.1.2"`` → ``"3"``
        ``"8.2.5"`` → ``"8"``
        ``"AC-1"``  → ``"AC"``

    Args:
        control_id: The control ID string.

    Returns:
        The top-level requirement family prefix.
    """
    # Dotted IDs (PCI DSS style): take the first segment
    if "." in control_id:
        return control_id.split(".")[0]
    # Hyphenated IDs (NIST style): take the prefix before the hyphen
    if "-" in control_id:
        return control_id.split("-")[0]
    return control_id


def resolve_meta_requirements(
    *,
    results: list[MappedResult],
    meta_control_ids: set[str],
) -> list[MappedResult]:
    """Resolve meta-requirements by aggregating sibling compliance.

    For each control in ``meta_control_ids``, finds sibling controls
    in the same requirement family and aggregates their compliance
    verdicts.  Governance controls are **always** overridden — even
    if they already have a direct rationale from chunk matching.

    This function should be called **after** gap rationale generation
    so that all sibling controls have rationales available for
    aggregation.

    Args:
        results: List of MappedResult objects (may be mutated in place).
        meta_control_ids: Set of control IDs that have been classified
            as meta-requirements (via LLM).

    Returns:
        The same list of MappedResult objects, with meta-requirements
        resolved.
    """
    if not results or not meta_control_ids:
        return results

    # Index results by requirement family for sibling lookups
    family_map: dict[str, list[MappedResult]] = {}
    for r in results:
        family = _get_requirement_family(r.control.control_id)
        family_map.setdefault(family, []).append(r)

    for result in results:
        if result.control.control_id not in meta_control_ids:
            continue

        # Find sibling controls in the same family (non-meta, with rationale)
        family = _get_requirement_family(result.control.control_id)
        siblings = [
            r
            for r in family_map.get(family, [])
            if r.control.control_id != result.control.control_id
            and r.control.control_id not in meta_control_ids
            and isinstance(r.rationale, MappingRationale)
        ]

        if not siblings:
            # No evaluated siblings — can't aggregate
            continue

        # Aggregate sibling verdicts
        from ctrlmap.models.schemas import ComplianceLevel

        non_compliant = [
            s
            for s in siblings
            if s.rationale.compliance_level == ComplianceLevel.NON_COMPLIANT  # type: ignore[union-attr]
        ]
        partial = [
            s
            for s in siblings
            if s.rationale.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT  # type: ignore[union-attr]
        ]

        has_direct_evidence = bool(result.supporting_chunks)

        if non_compliant:
            gap_ids = [s.control.control_id for s in non_compliant]

            if has_direct_evidence and isinstance(result.rationale, MappingRationale):
                # Control has direct evidence AND the LLM rated it —
                # preserve the LLM's verdict.  The evidence was already
                # verified for relevance in Step 1 of the pipeline.
                continue

            result.rationale = MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.90,
                explanation=(
                    f"Inferred from sibling controls: "
                    f"{len(non_compliant)} of {len(siblings)} evaluated "
                    f"controls in Requirement {family} are non-compliant "
                    f"({', '.join(gap_ids)}). This governance requirement "
                    f"cannot be met until all sibling controls are addressed."
                ),
            )
        elif partial:
            if has_direct_evidence and isinstance(result.rationale, MappingRationale):
                continue

            partial_ids = [s.control.control_id for s in partial]
            avg_score = sum(
                s.rationale.confidence_score  # type: ignore[union-attr,misc]
                for s in siblings
            ) / len(siblings)
            result.rationale = MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
                confidence_score=round(min(avg_score, 1.0), 2),
                explanation=(
                    f"Inferred from sibling controls: "
                    f"{len(partial)} of {len(siblings)} evaluated "
                    f"controls in Requirement {family} are partially "
                    f"compliant ({', '.join(partial_ids)}). Full compliance "
                    f"requires addressing remaining gaps."
                ),
            )
        else:
            # All siblings compliant — infer compliance for governance
            # controls that have no direct evidence.  This overrides any
            # gap rationale from Step 4, since the gap was generated
            # before sibling information was available.
            if has_direct_evidence:
                continue

            avg_score = sum(
                s.rationale.confidence_score  # type: ignore[union-attr,misc]
                for s in siblings
            ) / len(siblings)
            result.rationale = MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=round(min(avg_score, 1.0), 2),
                explanation=(
                    f"Inferred from sibling controls: all {len(siblings)} "
                    f"evaluated controls in Requirement "
                    f"{family} are compliant. "
                    f"Aggregated confidence from sibling assessments."
                ),
            )

    return results
