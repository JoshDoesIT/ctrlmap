"""Tests for multi-format output support in map_command.

TDD RED phase: The map command should support comma-separated output
formats to eliminate inconsistencies from multiple LLM runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ctrlmap.models.schemas import (
    ComplianceLevel,
    MappedResult,
    MappingRationale,
    ParsedChunk,
    SecurityControl,
)


@pytest.fixture()
def sample_results() -> list[MappedResult]:
    """A minimal set of mapping results for output testing."""
    return [
        MappedResult(
            control=SecurityControl(
                control_id="1.2.1",
                framework="PCI-DSS",
                title="PCI DSS 1.2.1",
                description="NSC rulesets are defined, implemented, maintained.",
            ),
            supporting_chunks=[
                ParsedChunk(
                    chunk_id="chunk-001",
                    document_name="network_policy.pdf",
                    page_number=2,
                    raw_text="Configuration standards for NSC rulesets must be defined.",
                    section_header="2.1 Firewall Configuration",
                    embedding=None,
                ),
            ],
            rationale=MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=1.0,
                explanation="Policy matches the control requirement.",
            ),
        ),
    ]


class TestMultiFormatEmit:
    """_emit_results should write to multiple format/path pairs in one call."""

    def test_emit_writes_multiple_formats(
        self,
        sample_results: list[MappedResult],
        tmp_path: Path,
    ) -> None:
        """A single _emit_results call with comma-separated formats creates all files."""
        from ctrlmap.map.map_command import _emit_results

        md_path = tmp_path / "report.md"
        json_path = tmp_path / "report.json"
        html_path = tmp_path / "report.html"

        _emit_results(
            sample_results,
            output_format="markdown,json,html",
            output_path=Path(f"{md_path},{json_path},{html_path}"),
        )

        assert md_path.exists(), "Markdown file not created"
        assert json_path.exists(), "JSON file not created"
        assert html_path.exists(), "HTML file not created"

    def test_emit_single_format_still_works(
        self,
        sample_results: list[MappedResult],
        tmp_path: Path,
    ) -> None:
        """Backward compatibility: a single format string still works."""
        from ctrlmap.map.map_command import _emit_results

        json_path = tmp_path / "report.json"

        _emit_results(
            sample_results,
            output_format="json",
            output_path=json_path,
        )

        assert json_path.exists(), "JSON file not created"

    def test_emit_multi_format_produces_identical_content(
        self,
        sample_results: list[MappedResult],
        tmp_path: Path,
    ) -> None:
        """Multi-format output uses the same results for all formats.

        Each format should contain the same control_id to prove they
        share the same underlying data (no re-computation).
        """
        from ctrlmap.map.map_command import _emit_results

        md_path = tmp_path / "report.md"
        json_path = tmp_path / "report.json"

        _emit_results(
            sample_results,
            output_format="markdown,json",
            output_path=Path(f"{md_path},{json_path}"),
        )

        md_content = md_path.read_text()
        json_content = json_path.read_text()

        assert "1.2.1" in md_content, "Control ID missing from markdown"
        assert "1.2.1" in json_content, "Control ID missing from JSON"

    def test_emit_format_count_mismatch_raises(
        self,
        sample_results: list[MappedResult],
        tmp_path: Path,
    ) -> None:
        """Mismatched format/path counts should raise ValueError."""
        from ctrlmap.map.map_command import _emit_results

        with pytest.raises(ValueError, match=r"format.*path.*count"):
            _emit_results(
                sample_results,
                output_format="markdown,json",
                output_path=tmp_path / "only_one.md",
            )
