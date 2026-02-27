"""Markdown export formatter for compliance mapping results.

Converts ``MappedResult`` objects into a structured Markdown table
for human-readable compliance reports.

Ref: GitHub Issue #22.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ctrlmap.models.schemas import (
    InsufficientEvidence,
    MappedResult,
    MappingRationale,
)


def format_markdown(results: list[MappedResult]) -> str:
    """Format mapping results as a Markdown table.

    Produces a structured table with columns for control ID, framework,
    title, supporting chunks, and rationale.

    Args:
        results: List of MappedResult objects to format.

    Returns:
        A Markdown string containing the formatted table.
    """
    lines: list[str] = []
    lines.append("# Compliance Mapping Results")
    lines.append("")

    if not results:
        lines.append("No mapping results to display.")
        return "\n".join(lines) + "\n"

    # Table header
    lines.append("| Control ID | Framework | Title | Supporting Chunks | Rationale |")
    lines.append("|------------|-----------|-------|-------------------|-----------|")

    for result in results:
        control = result.control
        chunk_ids = ", ".join(c.chunk_id for c in result.supporting_chunks)
        rationale_text = _format_rationale(result.rationale)

        lines.append(
            f"| {control.control_id} "
            f"| {control.framework} "
            f"| {control.title} "
            f"| {chunk_ids} "
            f"| {rationale_text} |"
        )

    lines.append("")
    return "\n".join(lines) + "\n"


def export_markdown(results: list[MappedResult], path: Path) -> None:
    """Write mapping results as Markdown to disk atomically.

    Args:
        results: List of MappedResult objects to export.
        path: Output file path.
    """
    content = format_markdown(results)
    _atomic_write(path, content)


def _format_rationale(
    rationale: MappingRationale | InsufficientEvidence | None,
) -> str:
    """Format a union-type rationale for display in Markdown."""
    if rationale is None:
        return "N/A"
    if isinstance(rationale, MappingRationale):
        status = "Compliant" if rationale.is_compliant else "Non-compliant"
        return f"{status} ({rationale.confidence_score:.2f}): {rationale.explanation}"
    return f"Insufficient evidence: {rationale.reason}"


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
