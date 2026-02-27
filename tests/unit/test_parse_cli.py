"""Tests for the ctrlmap parse CLI subcommand.

TDD RED phase: Tests define the expected behavior of the parse
subcommand before implementation. Ref: GitHub Issue #9.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ctrlmap.cli import app

runner = CliRunner()

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class TestParseCommand:
    """Tests for the parse subcommand."""

    def test_parse_command_requires_input_flag(self) -> None:
        """Running parse without --input should show usage error."""
        result = runner.invoke(app, ["parse"])
        assert result.exit_code != 0
        assert (
            "Missing" in result.output
            or "Usage" in result.output
            or "required" in result.output.lower()
        )

    def test_parse_command_rejects_nonexistent_input(self) -> None:
        """--input with a nonexistent path should produce a clear error."""
        result = runner.invoke(
            app, ["parse", "--input", "/nonexistent/file.pdf", "--output", "/tmp/out.jsonl"]
        )
        assert result.exit_code != 0

    def test_parse_command_produces_jsonl_output(self, tmp_path: Path) -> None:
        """Parse should produce a valid .jsonl file with one JSON object per line."""
        output_path = tmp_path / "output.jsonl"

        result = runner.invoke(
            app,
            [
                "parse",
                "--input",
                str(FIXTURE_DIR / "single_column.pdf"),
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert output_path.exists(), "Output file was not created"

        # Each line should be valid JSON
        lines = output_path.read_text().strip().split("\n")
        assert len(lines) >= 1

        for line in lines:
            obj = json.loads(line)
            assert "chunk_id" in obj
            assert "raw_text" in obj
            assert "document_name" in obj
            assert "page_number" in obj

    def test_parse_command_supports_strategy_flag(self, tmp_path: Path) -> None:
        """--strategy flag should be accepted (semantic or fixed)."""
        output_path = tmp_path / "output.jsonl"

        result = runner.invoke(
            app,
            [
                "parse",
                "--input",
                str(FIXTURE_DIR / "single_column.pdf"),
                "--output",
                str(output_path),
                "--strategy",
                "fixed",
            ],
        )

        # Should not fail on valid strategy
        assert result.exit_code == 0, f"Command failed: {result.output}"

    def test_parse_help_shows_expected_flags(self) -> None:
        """parse --help should document all expected flags."""
        import re

        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0
        # Strip ANSI escape codes (Rich renders colored output on CI)
        clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "--input" in clean
        assert "--output" in clean
        assert "--strategy" in clean
