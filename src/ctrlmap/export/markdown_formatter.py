"""Markdown export formatter for compliance mapping results.

Converts ``MappedResult`` objects into a structured Markdown table
for human-readable compliance reports.

Ref: GitHub Issue #22.
"""

from __future__ import annotations

from pathlib import Path

from ctrlmap.models.schemas import (
    ComplianceLevel,
    InsufficientEvidence,
    MappedResult,
    MappingRationale,
)


def format_markdown(results: list[MappedResult]) -> str:
    """Format mapping results as Markdown with one section per control.

    Each control gets its own heading with verdict, rationale, and an
    evidence table showing source document, page, section, and a text
    excerpt for each supporting chunk.

    Args:
        results: List of MappedResult objects to format.

    Returns:
        A Markdown string containing the formatted report.
    """
    lines: list[str] = []
    lines.append("# Compliance Mapping Results")
    lines.append("")

    if not results:
        lines.append("No mapping results to display.")
        return "\n".join(lines) + "\n"

    for result in results:
        ctrl = result.control
        verdict, rationale_text = _format_rationale(result.rationale)

        # Control heading
        lines.append(f"## {ctrl.control_id} — {ctrl.title}")
        lines.append("")
        lines.append(f"**Framework:** {ctrl.framework} | **Verdict:** {verdict}")
        lines.append("")

        # Rationale
        if rationale_text:
            lines.append(f"**Rationale:** {rationale_text}")
            lines.append("")

        # Evidence table
        if result.supporting_chunks:
            lines.append("**Supporting Evidence:**")
            lines.append("")
            lines.append("| # | Source | Page | Section | Excerpt |")
            lines.append("|---|--------|------|---------|---------|")

            for i, chunk in enumerate(result.supporting_chunks, 1):
                source = chunk.document_name
                page = chunk.page_number
                section = chunk.section_header or "—"
                excerpt = _truncate(chunk.raw_text, 120)
                lines.append(f"| {i} | {source} | {page} | {section} | {excerpt} |")

            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines) + "\n"


def export_markdown(results: list[MappedResult], path: Path) -> None:
    """Write mapping results as Markdown to disk atomically.

    Args:
        results: List of MappedResult objects to export.
        path: Output file path.
    """
    from ctrlmap.export._io import atomic_write

    content = format_markdown(results)
    atomic_write(path, content)


def _format_rationale(
    rationale: MappingRationale | InsufficientEvidence | None,
) -> tuple[str, str]:
    """Format a union-type rationale into a verdict badge and explanation.

    Returns:
        A tuple of (verdict_string, explanation_string).
    """
    if rationale is None:
        return ("N/A", "")
    if isinstance(rationale, MappingRationale):
        level = rationale.compliance_level
        if level == ComplianceLevel.FULLY_COMPLIANT:
            icon, status = "\u2705", "Compliant"
        elif level == ComplianceLevel.PARTIALLY_COMPLIANT:
            icon, status = "\U0001f7e1", "Partially compliant"
        else:
            icon, status = "\u26a0\ufe0f", "Non-compliant"
        verdict = f"{icon} {status} ({rationale.confidence_score:.2f})"
        return (verdict, rationale.explanation)
    return ("Insufficient evidence", rationale.reason)


def _truncate(text: str, max_len: int = 120) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
