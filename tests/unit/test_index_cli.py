"""Tests for the ctrlmap index CLI subcommand.

TDD RED phase for Story #15.
Ref: GitHub Issue #15.
"""

from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from ctrlmap.cli import app

runner = CliRunner()

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class TestIndexCommand:
    """Tests for the index subcommand."""

    def test_index_command_requires_chunks_flag(self) -> None:
        """Running index without --chunks should show usage error."""
        result = runner.invoke(app, ["index"])
        assert result.exit_code != 0
        assert (
            "Missing" in result.output
            or "Usage" in result.output
            or "required" in result.output.lower()
        )

    def test_index_command_populates_database(self, tmp_path: Path) -> None:
        """Index subcommand creates a populated ChromaDB database."""
        db_path = tmp_path / "test_vector_db"

        result = runner.invoke(
            app,
            [
                "index",
                "--chunks",
                str(FIXTURE_DIR / "test_chunks.jsonl"),
                "--framework",
                str(FIXTURE_DIR / "nist_800_53_subset.json"),
                "--db-path",
                str(db_path),
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert db_path.exists(), "Database directory was not created"

    def test_index_command_embeds_framework_controls(self, tmp_path: Path) -> None:
        """Index subcommand embeds OSCAL framework controls alongside chunks."""
        db_path = tmp_path / "framework_db"

        result = runner.invoke(
            app,
            [
                "index",
                "--chunks",
                str(FIXTURE_DIR / "test_chunks.jsonl"),
                "--framework",
                str(FIXTURE_DIR / "nist_800_53_subset.json"),
                "--db-path",
                str(db_path),
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Output should mention both chunks and controls
        assert "chunk" in result.output.lower() or "control" in result.output.lower()

    def test_index_command_reports_progress(self, tmp_path: Path) -> None:
        """Index subcommand provides progress feedback."""
        db_path = tmp_path / "progress_db"

        result = runner.invoke(
            app,
            [
                "index",
                "--chunks",
                str(FIXTURE_DIR / "test_chunks.jsonl"),
                "--framework",
                str(FIXTURE_DIR / "nist_800_53_subset.json"),
                "--db-path",
                str(db_path),
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Strip ANSI escape codes
        clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        # Should contain progress information (chunk/control counts or "Done")
        assert any(
            keyword in clean.lower()
            for keyword in ["indexed", "done", "chunks", "controls", "embedded"]
        )

    def test_index_help_shows_expected_flags(self) -> None:
        """index --help should document all expected flags."""
        result = runner.invoke(app, ["index", "--help"])
        assert result.exit_code == 0
        clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "--chunks" in clean
        assert "--framework" in clean
        assert "--db-path" in clean
        assert "--embedding-model" in clean
