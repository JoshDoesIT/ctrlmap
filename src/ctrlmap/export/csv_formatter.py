"""CSV export formatter for compliance mapping results.

Converts ``MappedResult`` objects into CSV format with one row per
control-chunk pair.

Ref: GitHub Issue #22.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from ctrlmap.models.schemas import (
    InsufficientEvidence,
    MappedResult,
    MappingRationale,
)

_COLUMNS = [
    "control_id",
    "framework",
    "title",
    "chunk_id",
    "raw_text",
    "is_compliant",
    "compliance_level",
    "confidence_score",
    "rationale",
]


def format_csv(results: list[MappedResult]) -> str:
    """Format mapping results as a CSV string.

    Produces one row per control-chunk pair. Controls with multiple
    supporting chunks produce multiple rows.

    Args:
        results: List of MappedResult objects to format.

    Returns:
        A UTF-8 CSV string with header row.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_COLUMNS)

    for result in results:
        rationale_fields = _extract_rationale_fields(result.rationale)

        for chunk in result.supporting_chunks:
            writer.writerow(
                [
                    result.control.control_id,
                    result.control.framework,
                    result.control.title,
                    chunk.chunk_id,
                    chunk.raw_text,
                    rationale_fields["is_compliant"],
                    rationale_fields["compliance_level"],
                    rationale_fields["confidence_score"],
                    rationale_fields["rationale"],
                ]
            )

    return output.getvalue()


def export_csv(results: list[MappedResult], path: Path) -> None:
    """Write mapping results as CSV to disk atomically.

    Uses a temporary file and rename to prevent partial writes on failure.

    Args:
        results: List of MappedResult objects to export.
        path: Output file path.
    """
    from ctrlmap.export._io import atomic_write

    content = format_csv(results)
    atomic_write(path, content)


def _extract_rationale_fields(
    rationale: MappingRationale | InsufficientEvidence | None,
) -> dict[str, str]:
    """Extract display fields from a union-type rationale."""
    if rationale is None:
        return {"is_compliant": "", "compliance_level": "", "confidence_score": "", "rationale": ""}
    if isinstance(rationale, MappingRationale):
        return {
            "is_compliant": str(rationale.is_compliant),
            "compliance_level": rationale.compliance_level.value,
            "confidence_score": str(rationale.confidence_score),
            "rationale": rationale.explanation,
        }
    return {
        "is_compliant": "",
        "compliance_level": "",
        "confidence_score": "",
        "rationale": f"InsufficientEvidence: {rationale.reason}",
    }
