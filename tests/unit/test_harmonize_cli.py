"""Tests for the `ctrlmap harmonize` CLI subcommand.

TDD RED phase: Story #20, harmonize subcommand.
Ref: GitHub Issue #20.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ctrlmap.cli import app
from ctrlmap.models.schemas import CommonControl

runner = CliRunner()


class TestHarmonizeCommand:
    """Story #20: Harmonize CLI subcommand tests."""

    def test_harmonize_command_accepts_directory(self, tmp_path: Path) -> None:
        """Harmonize command accepts --inputs directory flag."""
        inputs_dir = tmp_path / "inputs"
        inputs_dir.mkdir()

        # Create a minimal OSCAL framework file in the inputs dir
        framework = {
            "catalog": {
                "uuid": "test",
                "metadata": {"title": "Test", "version": "1.0"},
                "groups": [
                    {
                        "id": "ac",
                        "title": "AC",
                        "controls": [
                            {
                                "id": "ac-1",
                                "title": "Policy",
                                "props": [{"name": "label", "value": "AC-1"}],
                                "parts": [
                                    {
                                        "id": "ac-1_smt",
                                        "name": "statement",
                                        "prose": "Access control policy.",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }
        (inputs_dir / "framework1.json").write_text(json.dumps(framework))

        mock_cc = CommonControl(
            common_id="CC-001",
            theme="Access Control",
            unified_description="Unified access control requirement.",
            source_references=["AC-1"],
        )

        with (
            patch("ctrlmap.map.harmonize_command.cluster_controls", return_value=[mock_cc]),
            patch("ctrlmap.map.harmonize_command.parse_oscal_catalog"),
        ):
            result = runner.invoke(
                app,
                ["harmonize", "--inputs", str(inputs_dir)],
            )
        assert result.exit_code == 0

    def test_harmonize_command_outputs_common_controls(self, tmp_path: Path) -> None:
        """Harmonize command outputs JSON with CommonControl objects."""
        inputs_dir = tmp_path / "inputs"
        inputs_dir.mkdir()

        framework = {
            "catalog": {
                "uuid": "test",
                "metadata": {"title": "Test", "version": "1.0"},
                "groups": [
                    {
                        "id": "sc",
                        "title": "SC",
                        "controls": [
                            {
                                "id": "sc-28",
                                "title": "Encryption",
                                "props": [{"name": "label", "value": "SC-28"}],
                                "parts": [
                                    {
                                        "id": "sc-28_smt",
                                        "name": "statement",
                                        "prose": "Encrypt data at rest.",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }
        (inputs_dir / "framework1.json").write_text(json.dumps(framework))

        mock_ccs = [
            CommonControl(
                common_id="CC-001",
                theme="Encryption at Rest",
                unified_description="Protect data at rest.",
                source_references=["SC-28", "SOC2-CC6.1", "ISO-A.10.1.1"],
            )
        ]

        with (
            patch("ctrlmap.map.harmonize_command.cluster_controls", return_value=mock_ccs),
            patch("ctrlmap.map.harmonize_command.parse_oscal_catalog"),
        ):
            result = runner.invoke(
                app,
                ["harmonize", "--inputs", str(inputs_dir)],
            )
        assert result.exit_code == 0
        # Extract JSON array from mixed console output
        output = result.output
        start = output.find("[")
        end = output.rfind("]") + 1
        assert start >= 0 and end > start
        parsed = json.loads(output[start:end])
        assert isinstance(parsed, list)
        assert parsed[0]["common_id"] == "CC-001"
        assert len(parsed[0]["source_references"]) == 3
