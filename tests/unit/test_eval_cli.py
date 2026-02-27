"""Tests for the `ctrlmap eval` CLI subcommand.

TDD RED phase: Story #23, eval subcommand.
Ref: GitHub Issue #23.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ctrlmap.cli import app

runner = CliRunner()


@pytest.fixture()
def golden_dataset(tmp_path: Path) -> Path:
    """Create a minimal golden dataset JSON file."""
    data = {
        "queries": [
            {
                "query": "AC-1: Policy and Procedures. Develop access control policies.",
                "expected_ids": ["chunk-ac-001", "chunk-ac-002"],
            },
            {
                "query": "SC-28: Protection of Information at Rest. Protect data at rest.",
                "expected_ids": ["chunk-enc-001"],
            },
        ]
    }
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestEvalCommand:
    """Story #23: eval CLI subcommand."""

    def test_eval_command_requires_golden_dataset(self, tmp_path: Path) -> None:
        """eval subcommand errors when --golden-dataset is not provided."""
        result = runner.invoke(app, ["eval", "--db-path", str(tmp_path)])
        assert result.exit_code != 0

    def test_eval_command_accepts_golden_dataset(
        self, golden_dataset: Path, tmp_path: Path
    ) -> None:
        """eval subcommand accepts --golden-dataset and --db-path flags."""
        from ctrlmap.index.embedder import Embedder
        from ctrlmap.index.vector_store import VectorStore
        from ctrlmap.models.schemas import ParsedChunk

        # Set up a vector store with indexed chunks
        store = VectorStore(db_path=tmp_path / "eval_db")
        embedder = Embedder()
        chunks = [
            ParsedChunk(
                chunk_id="chunk-ac-001",
                document_name="policy.pdf",
                page_number=1,
                raw_text="All employees must follow access control policies.",
                embedding=embedder.embed_text("All employees must follow access control policies."),
            ),
            ParsedChunk(
                chunk_id="chunk-enc-001",
                document_name="policy.pdf",
                page_number=5,
                raw_text="All data at rest must be encrypted using AES-256.",
                embedding=embedder.embed_text("All data at rest must be encrypted using AES-256."),
            ),
        ]
        store.index_chunks("chunks", chunks)

        result = runner.invoke(
            app,
            [
                "eval",
                "--db-path",
                str(tmp_path / "eval_db"),
                "--golden-dataset",
                str(golden_dataset),
                "--metric",
                "precision",
            ],
        )
        # Should complete without crashing
        assert result.exit_code == 0

    def test_eval_computes_precision(self, golden_dataset: Path, tmp_path: Path) -> None:
        """eval subcommand computes and displays precision metric."""
        from ctrlmap.index.embedder import Embedder
        from ctrlmap.index.vector_store import VectorStore
        from ctrlmap.models.schemas import ParsedChunk

        store = VectorStore(db_path=tmp_path / "prec_db")
        embedder = Embedder()
        chunks = [
            ParsedChunk(
                chunk_id="chunk-ac-001",
                document_name="policy.pdf",
                page_number=1,
                raw_text="All employees must follow access control policies.",
                embedding=embedder.embed_text("All employees must follow access control policies."),
            ),
        ]
        store.index_chunks("chunks", chunks)

        result = runner.invoke(
            app,
            [
                "eval",
                "--db-path",
                str(tmp_path / "prec_db"),
                "--golden-dataset",
                str(golden_dataset),
                "--metric",
                "precision",
            ],
        )
        assert result.exit_code == 0
        assert "precision" in result.output.lower()

    def test_eval_computes_recall(self, golden_dataset: Path, tmp_path: Path) -> None:
        """eval subcommand computes and displays recall metric."""
        from ctrlmap.index.embedder import Embedder
        from ctrlmap.index.vector_store import VectorStore
        from ctrlmap.models.schemas import ParsedChunk

        store = VectorStore(db_path=tmp_path / "recall_db")
        embedder = Embedder()
        chunks = [
            ParsedChunk(
                chunk_id="chunk-ac-001",
                document_name="policy.pdf",
                page_number=1,
                raw_text="All employees must follow access control policies.",
                embedding=embedder.embed_text("All employees must follow access control policies."),
            ),
        ]
        store.index_chunks("chunks", chunks)

        result = runner.invoke(
            app,
            [
                "eval",
                "--db-path",
                str(tmp_path / "recall_db"),
                "--golden-dataset",
                str(golden_dataset),
                "--metric",
                "recall",
            ],
        )
        assert result.exit_code == 0
        assert "recall" in result.output.lower()

    def test_eval_exit_code_reflects_threshold(self, golden_dataset: Path, tmp_path: Path) -> None:
        """eval subcommand returns exit code 1 when below threshold."""
        from ctrlmap.index.vector_store import VectorStore

        # Empty store will produce 0.0 scores, which must fail a 0.9 threshold
        empty_store = VectorStore(db_path=tmp_path / "empty_eval_db")
        empty_store.get_or_create_collection("chunks")

        result = runner.invoke(
            app,
            [
                "eval",
                "--db-path",
                str(tmp_path / "empty_eval_db"),
                "--golden-dataset",
                str(golden_dataset),
                "--metric",
                "precision",
                "--threshold",
                "0.9",
            ],
        )
        assert result.exit_code == 1

    def test_eval_help_shows_expected_flags(self) -> None:
        """eval help output includes expected flags."""
        result = runner.invoke(app, ["eval", "--help"])
        assert result.exit_code == 0
        assert "--golden-dataset" in result.output
        assert "--metric" in result.output
        assert "--db-path" in result.output
        assert "ragas" in result.output

    def test_eval_ragas_exits_gracefully_without_package(
        self, golden_dataset: Path, tmp_path: Path
    ) -> None:
        """eval --metric ragas exits with code 1 when ragas is not installed."""
        from ctrlmap.index.vector_store import VectorStore

        store = VectorStore(db_path=tmp_path / "ragas_db")
        store.get_or_create_collection("chunks")

        result = runner.invoke(
            app,
            [
                "eval",
                "--db-path",
                str(tmp_path / "ragas_db"),
                "--golden-dataset",
                str(golden_dataset),
                "--metric",
                "ragas",
            ],
        )
        assert result.exit_code == 1
