"""OSCAL JSON export formatter for compliance mapping results.

Converts ``MappedResult`` objects into an OSCAL-aligned assessment
results structure for federal/international interoperability.

Ref: GitHub Issue #22.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ctrlmap.models.schemas import (
    InsufficientEvidence,
    MappedResult,
    MappingRationale,
)


def format_oscal(results: list[MappedResult]) -> dict[str, Any]:
    """Format mapping results as an OSCAL-aligned assessment results dict.

    Produces a structure compatible with the NIST OSCAL Assessment Results
    model, including findings and observations per control.

    Args:
        results: List of MappedResult objects to format.

    Returns:
        A dictionary conforming to OSCAL assessment-results structure.
    """
    findings: list[dict[str, Any]] = []

    for result in results:
        finding: dict[str, Any] = {
            "uuid": str(uuid.uuid4()),
            "title": f"{result.control.control_id}: {result.control.title}",
            "description": result.control.description,
            "target": {
                "type": "objective-id",
                "target-id": result.control.control_id,
                "status": {"state": _determine_state(result.rationale)},
            },
            "related-observations": [],
        }

        for chunk in result.supporting_chunks:
            observation: dict[str, Any] = {
                "uuid": str(uuid.uuid4()),
                "description": chunk.raw_text,
                "methods": ["EXAMINE"],
                "subjects": [
                    {
                        "subject-uuid": str(uuid.uuid4()),
                        "type": "component",
                        "title": chunk.document_name,
                        "props": [
                            {"name": "chunk-id", "value": chunk.chunk_id},
                            {
                                "name": "page-number",
                                "value": str(chunk.page_number),
                            },
                        ],
                    }
                ],
            }
            finding["related-observations"].append({"observation-uuid": observation["uuid"]})

        if result.rationale is not None:
            finding["remarks"] = _format_rationale(result.rationale)

        findings.append(finding)

    return {
        "assessment-results": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": "ctrlmap Assessment Results",
                "last-modified": datetime.now(tz=timezone.utc).isoformat(),  # noqa: UP017
                "version": "1.0.0",
                "oscal-version": "1.1.2",
            },
            "results": findings,
        }
    }


def export_oscal(results: list[MappedResult], path: Path) -> None:
    """Write mapping results as OSCAL JSON to disk atomically.

    Args:
        results: List of MappedResult objects to export.
        path: Output file path.
    """
    oscal_dict = format_oscal(results)
    content = json.dumps(oscal_dict, indent=2, ensure_ascii=False)
    _atomic_write(path, content)


def _determine_state(
    rationale: MappingRationale | InsufficientEvidence | None,
) -> str:
    """Determine the OSCAL finding state from a rationale."""
    if rationale is None:
        return "not-satisfied"
    if isinstance(rationale, MappingRationale):
        return "satisfied" if rationale.is_compliant else "not-satisfied"
    return "not-satisfied"


def _format_rationale(
    rationale: MappingRationale | InsufficientEvidence,
) -> str:
    """Format a rationale as a remarks string."""
    if isinstance(rationale, MappingRationale):
        return (
            f"Compliant: {rationale.is_compliant}, "
            f"Confidence: {rationale.confidence_score}, "
            f"Explanation: {rationale.explanation}"
        )
    return f"Insufficient evidence: {rationale.reason}. Required: {rationale.required_context}"


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.rename(path)
