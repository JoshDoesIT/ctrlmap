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
        raw_text="All data at rest must be encrypted using AES-256 or equivalent standards.",
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

    def test_markdown_export_uses_section_per_control(
        self, sample_results: list[MappedResult]
    ) -> None:
        """Markdown output uses a heading per control instead of one flat table."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(sample_results)

        # Each control gets its own ## heading
        assert "## AC-1" in md_output
        assert "## SC-28" in md_output

    def test_markdown_export_shows_verdict_and_rationale(
        self, sample_results: list[MappedResult]
    ) -> None:
        """Markdown output includes the compliance verdict and rationale text."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(sample_results)

        assert "Compliant" in md_output
        assert "0.92" in md_output
        assert "Policy directly addresses" in md_output
        assert "Insufficient evidence" in md_output.lower() or "Insufficient" in md_output

    def test_markdown_export_shows_document_name_not_uuid(
        self, sample_results: list[MappedResult]
    ) -> None:
        """Evidence table shows document names instead of raw UUIDs."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(sample_results)

        # Should show the human-readable source document name
        assert "policy.pdf" in md_output
        # Should NOT show raw chunk UUIDs
        assert "chunk-001" not in md_output
        assert "chunk-002" not in md_output

    def test_markdown_export_shows_page_and_section(
        self, sample_results: list[MappedResult]
    ) -> None:
        """Evidence table includes page numbers and section headers."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(sample_results)

        assert "Page" in md_output or "page" in md_output
        assert "Access Control" in md_output
        assert "Encryption" in md_output

    def test_markdown_export_shows_text_excerpt(self, sample_results: list[MappedResult]) -> None:
        """Evidence table includes a text excerpt from each chunk."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(sample_results)

        # Should see part of the raw_text (truncated or full)
        assert "access control policies" in md_output.lower()
        assert "encrypted using AES-256" in md_output

    def test_markdown_export_handles_empty_results(self, empty_results: list[MappedResult]) -> None:
        """Markdown export with no results produces a header-only table or message."""
        from ctrlmap.export.markdown_formatter import format_markdown

        md_output = format_markdown(empty_results)

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
                        raw_text="Accounts are managed centrally by the IT department team.",
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


class TestHtmlExport:
    """HTML report formatter tests."""

    def test_html_export_produces_valid_html(self, sample_results: list[MappedResult]) -> None:
        """HTML output contains a complete HTML document with expected structure."""
        from ctrlmap.export.html_formatter import format_html

        html_output = format_html(sample_results)

        assert "<!DOCTYPE html>" in html_output
        assert "</html>" in html_output
        assert "<style>" in html_output

    def test_html_export_shows_control_ids(self, sample_results: list[MappedResult]) -> None:
        """HTML output contains the control IDs."""
        from ctrlmap.export.html_formatter import format_html

        html_output = format_html(sample_results)

        assert "AC-1" in html_output
        assert "SC-28" in html_output

    def test_html_export_shows_document_name_not_uuid(
        self, sample_results: list[MappedResult]
    ) -> None:
        """HTML evidence shows document names instead of raw UUIDs."""
        from ctrlmap.export.html_formatter import format_html

        html_output = format_html(sample_results)

        assert "policy.pdf" in html_output
        assert "chunk-001" not in html_output
        assert "chunk-002" not in html_output

    def test_html_export_shows_evidence_details(self, sample_results: list[MappedResult]) -> None:
        """HTML evidence includes page numbers, section headers, and text excerpts."""
        from ctrlmap.export.html_formatter import format_html

        html_output = format_html(sample_results)

        assert "Access Control" in html_output
        assert "Encryption" in html_output
        assert "access control policies" in html_output.lower()

    def test_html_export_handles_empty_results(self, empty_results: list[MappedResult]) -> None:
        """HTML export with no results produces valid HTML."""
        from ctrlmap.export.html_formatter import format_html

        html_output = format_html(empty_results)

        assert "<!DOCTYPE html>" in html_output
        assert "No mapping results" in html_output

    def test_html_export_writes_to_disk(
        self, sample_results: list[MappedResult], tmp_path: Path
    ) -> None:
        """HTML export writes a self-contained file to disk."""
        from ctrlmap.export.html_formatter import export_html

        output_path = tmp_path / "report.html"
        export_html(sample_results, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "AC-1" in content

    def test_html_export_has_tab_navigation(self, sample_results: list[MappedResult]) -> None:
        """HTML report has tabs for Framework Gap and Policy Coverage views."""
        from ctrlmap.export.html_formatter import format_html

        html_output = format_html(sample_results)

        assert "Framework Gap" in html_output or "framework-gap" in html_output
        assert "Policy Coverage" in html_output or "policy-coverage" in html_output

    def test_html_export_policy_view_groups_by_document(
        self, sample_results: list[MappedResult]
    ) -> None:
        """Policy coverage view groups evidence by source document."""
        from ctrlmap.export.html_formatter import format_html

        html_output = format_html(sample_results)

        # The policy view should have the document names as section headings
        # and show which controls each chunk maps to
        assert "policy.pdf" in html_output
        # Controls should appear in the policy view context
        assert "AC-1" in html_output
        assert "SC-28" in html_output
