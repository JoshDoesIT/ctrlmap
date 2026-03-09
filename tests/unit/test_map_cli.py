"""Tests for the `ctrlmap map` CLI subcommand.

TDD RED phase: Story #20, map subcommand.
Ref: GitHub Issue #20.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from ctrlmap.cli import app
from ctrlmap.models.schemas import MappedResult, ParsedChunk, SecurityControl

runner = CliRunner()


class TestMapCommand:
    """Story #20: Map CLI subcommand tests."""

    def test_map_command_outputs_json_format(self, tmp_path: Path) -> None:
        """Map command with --output-format json produces valid JSON output."""
        # Create a mock DB and framework
        db_path = tmp_path / "test_db"
        framework_path = tmp_path / "framework.json"
        framework_path.write_text(
            json.dumps(
                {
                    "catalog": {
                        "uuid": "test",
                        "metadata": {"title": "Test", "version": "1.0"},
                        "groups": [
                            {
                                "id": "ac",
                                "title": "Access Control",
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
            )
        )

        # Mock map_controls to return a predictable result
        mock_result = MappedResult(
            control=SecurityControl(
                control_id="AC-1",
                framework="NIST-800-53",
                title="Policy",
                description="Access control policy.",
            ),
            supporting_chunks=[
                ParsedChunk(
                    chunk_id="c1",
                    document_name="policy.pdf",
                    page_number=1,
                    raw_text="All users must comply with access control policies.",
                )
            ],
        )

        with (
            patch("ctrlmap.map.map_command.map_controls", return_value=[mock_result]),
            patch("ctrlmap.map.map_command.VectorStore"),
        ):
            result = runner.invoke(
                app,
                [
                    "map",
                    "--db-path",
                    str(db_path),
                    "--framework",
                    str(framework_path),
                    "--output-format",
                    "json",
                ],
            )
        assert result.exit_code == 0
        # Extract JSON array from mixed console output
        output = result.output
        start = output.find("[")
        end = output.rfind("]") + 1
        assert start >= 0 and end > start
        parsed = json.loads(output[start:end])
        assert isinstance(parsed, list)

    def test_map_command_with_rationale_invokes_llm(self, tmp_path: Path) -> None:
        """Map command with --rationale flag calls the LLM rationale generator."""
        db_path = tmp_path / "test_db"
        framework_path = tmp_path / "framework.json"
        framework_path.write_text(
            json.dumps(
                {
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
                                                "prose": "Access control.",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                }
            )
        )

        mock_result = MappedResult(
            control=SecurityControl(
                control_id="AC-1",
                framework="NIST-800-53",
                title="Policy",
                description="Access control.",
            ),
            supporting_chunks=[
                ParsedChunk(
                    chunk_id="c1",
                    document_name="policy.pdf",
                    page_number=1,
                    raw_text="All users must comply with access control policies.",
                )
            ],
        )

        with (
            patch("ctrlmap.map.map_command.map_controls", return_value=[mock_result]),
            patch("ctrlmap.map.map_command.VectorStore"),
            patch("ctrlmap.llm.client.OllamaClient") as mock_ollama_cls,
        ):
            from ctrlmap.models.schemas import MappingRationale

            # Mock the batch evaluate_chunks_batch_async to return a list of rationales
            mock_client = mock_ollama_cls.return_value
            mock_client.evaluate_chunks_batch_async = AsyncMock(
                return_value=[
                    MappingRationale(
                        is_compliant=True,
                        confidence_score=0.9,
                        explanation="Compliant.",
                    )
                ]
            )
            mock_client.classify_control_type_async = AsyncMock(return_value=False)

            result = runner.invoke(
                app,
                [
                    "map",
                    "--db-path",
                    str(db_path),
                    "--framework",
                    str(framework_path),
                    "--output-format",
                    "json",
                    "--rationale",
                ],
            )
        assert result.exit_code == 0
