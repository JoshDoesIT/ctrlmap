"""Tests for export formatters (CSV, Markdown, OSCAL JSON).

TDD RED phase: Story #22, export formatters.
Ref: GitHub Issue #22.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from ctrlmap.models.schemas import (
    InsufficientEvidence,
    MappedResult,
    MappingRationale,
    ParsedChunk,
    SecurityControl,
)


@pytest.fixture()
def sample_results() -> list[MappedResult]:
    """Two MappedResults: one with MappingRationale, one with InsufficientEvidence."""
    control_ac1 = SecurityControl(
        control_id="AC-1",
        framework="NIST-800-53",
        title="Policy and Procedures",
        description="Develop access control policies.",
    )
    control_sc28 = SecurityControl(
        control_id="SC-28",
        framework="NIST-800-53",
        title="Protection of Information at Rest",
        description="Protect data at rest.",
    )
    chunk1 = ParsedChunk(
        chunk_id="chunk-001",
        document_name="policy.pdf",
        page_number=1,
        raw_text="All employees must follow access control policies and procedures.",
        section_header="Access Control",
    )
    chunk2 = ParsedChunk(
        chunk_id="chunk-002",
        document_name="policy.pdf",
        page_number=5,
        raw_text="All data at rest must be encrypted using AES-256.",
        section_header="Encryption",
    )
    return [
        MappedResult(
            control=control_ac1,
            supporting_chunks=[chunk1],
            rationale=MappingRationale(
                is_compliant=True,
                confidence_score=0.92,
                explanation="Policy directly addresses access control procedures.",
            ),
        ),
        MappedResult(
            control=control_sc28,
            supporting_chunks=[chunk2],
            rationale=InsufficientEvidence(
                reason="Chunk mentions encryption but lacks implementation details.",
                required_context="Specific encryption key management procedures.",
            ),
        ),
    ]


@pytest.fixture()
def empty_results() -> list[MappedResult]:
    """Empty results list."""
    return []


class TestCsvExport:
    """CSV export formatter tests."""

    def test_csv_export_produces_valid_csv(self, sample_results: list[MappedResult]) -> None:
        """CSV output is parseable and contains expected columns and rows."""
        from ctrlmap.export.csv_formatter import format_csv

        csv_output = format_csv(sample_results)

        # Should be valid CSV
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        # Header + data rows
        assert len(rows) == 3
        header = rows[0]
        assert "control_id" in header
        assert "framework" in header
        assert "title" in header
        assert "chunk_id" in header
        assert "raw_text" in header
        assert "rationale" in header

    def test_csv_export_handles_empty_results(self, empty_results: list[MappedResult]) -> None:
        """CSV export with no results produces header-only output."""
        from ctrlmap.export.csv_formatter import format_csv

        csv_output = format_csv(empty_results)
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)

        # Just the header row
        assert len(rows) == 1

    def test_csv_export_writes_atomically(
        self, sample_results: list[MappedResult], tmp_path: Path
    ) -> None:
        """CSV export writes to disk atomically (no partial files on failure)."""
        from ctrlmap.export.csv_formatter import export_csv

        output_path = tmp_path / "results.csv"
        export_csv(sample_results, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 3

    def test_csv_export_uses_utf8(self, sample_results: list[MappedResult], tmp_path: Path) -> None:
        """Exported CSV file uses UTF-8 encoding."""
        from ctrlmap.export.csv_formatter import export_csv

        output_path = tmp_path / "results.csv"
        export_csv(sample_results, output_path)

        raw_bytes = output_path.read_bytes()
        raw_bytes.decode("utf-8")  # Should not raise


class TestMarkdownExport:
    """Markdown export formatter tests."""

    def test_markdown_export_produces_valid_table(self, sample_results: list[MappedResult]) -> None:
        """Markdown output contains a structured table with expected columns."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(sample_results)

        # Should contain table header markers
        assert "| Control ID" in md_output
        assert "| Framework" in md_output or "Framework" in md_output
        assert "| Title" in md_output or "Title" in md_output
        # Should contain data
        assert "AC-1" in md_output
        assert "SC-28" in md_output

    def test_markdown_export_handles_empty_results(self, empty_results: list[MappedResult]) -> None:
        """Markdown export with no results produces a header-only table or message."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(empty_results)

        # Should still produce valid output (not crash)
        assert isinstance(md_output, str)
        assert len(md_output) > 0

    def test_markdown_export_writes_atomically(
        self, sample_results: list[MappedResult], tmp_path: Path
    ) -> None:
        """Markdown export writes to disk atomically."""
        from ctrlmap.export.markdown_formatter import export_markdown

        output_path = tmp_path / "results.md"
        export_markdown(sample_results, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "AC-1" in content


class TestOscalExport:
    """OSCAL JSON export formatter tests."""

    def test_oscal_json_export_produces_valid_json(
        self, sample_results: list[MappedResult]
    ) -> None:
        """OSCAL output is valid JSON with expected structure."""
        from ctrlmap.export.oscal_formatter import format_oscal

        oscal_dict = format_oscal(sample_results)

        # Should produce valid serializable dict
        json_str = json.dumps(oscal_dict)
        parsed = json.loads(json_str)

        # Should have top-level assessment-results structure
        assert "assessment-results" in parsed
        results = parsed["assessment-results"]
        assert "results" in results
        assert len(results["results"]) == 2

    def test_oscal_export_handles_empty_results(self, empty_results: list[MappedResult]) -> None:
        """OSCAL export with no results produces valid empty structure."""
        from ctrlmap.export.oscal_formatter import format_oscal

        oscal_dict = format_oscal(empty_results)
        assert "assessment-results" in oscal_dict
        assert oscal_dict["assessment-results"]["results"] == []

    def test_oscal_export_writes_atomically(
        self, sample_results: list[MappedResult], tmp_path: Path
    ) -> None:
        """OSCAL export writes to disk atomically."""
        from ctrlmap.export.oscal_formatter import export_oscal

        output_path = tmp_path / "results.json"
        export_oscal(sample_results, output_path)

        assert output_path.exists()
        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert "assessment-results" in content


class TestExportEdgeCases:
    """Cross-format edge case tests."""

    def test_export_handles_insufficient_evidence_rationale(
        self, sample_results: list[MappedResult]
    ) -> None:
        """All formatters handle InsufficientEvidence rationale correctly."""
        from ctrlmap.export.csv_formatter import format_csv
        from ctrlmap.export.markdown_formatter import format_markdown
        from ctrlmap.export.oscal_formatter import format_oscal

        # Should not crash on InsufficientEvidence
        csv_output = format_csv(sample_results)
        md_output = format_markdown(sample_results)
        oscal_output = format_oscal(sample_results)

        assert "InsufficientEvidence" in csv_output or "insufficient" in csv_output.lower()
        assert isinstance(md_output, str)
        assert isinstance(oscal_output, dict)

    def test_export_handles_none_rationale(self) -> None:
        """All formatters handle None rationale (no LLM invoked)."""
        from ctrlmap.export.csv_formatter import format_csv
        from ctrlmap.export.markdown_formatter import format_markdown
        from ctrlmap.export.oscal_formatter import format_oscal

        results = [
            MappedResult(
                control=SecurityControl(
                    control_id="AC-2",
                    framework="NIST-800-53",
                    title="Account Management",
                    description="Manage system accounts.",
                ),
                supporting_chunks=[
                    ParsedChunk(
                        chunk_id="chunk-003",
                        document_name="doc.pdf",
                        page_number=1,
                        raw_text="Accounts are managed centrally by IT department.",
                    ),
                ],
                rationale=None,
            ),
        ]

        csv_output = format_csv(results)
        md_output = format_markdown(results)
        oscal_output = format_oscal(results)

        assert "AC-2" in csv_output
        assert "AC-2" in md_output
        assert isinstance(oscal_output, dict)
