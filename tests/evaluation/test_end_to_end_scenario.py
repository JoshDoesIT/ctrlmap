"""P3: End-to-end pipeline scenario evaluation.

Runs the complete ctrlmap pipeline using the REAL ``enrich_with_rationale()``
entry point (not individual function calls) against a small, controlled
scenario and asserts structural correctness of outputs.

This validates that the actual production pipeline — including batch
evaluation, batch meta-classification, chunk truncation, and heuristic
pre-filtering — produces correct results.

This test is designed for fast iteration — 5 controls + 8 chunks runs
in seconds vs. the full demo's hundreds of controls taking minutes.

Ref: analysis_results.md — P3 recommendation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.map.enrichment import enrich_with_rationale
from ctrlmap.map.mapper import map_controls
from ctrlmap.models.schemas import MappingRationale, ParsedChunk, SecurityControl

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "e2e_scenario.json"


def _load_scenario() -> dict:
    """Load the end-to-end scenario fixture."""
    with FIXTURE_PATH.open() as f:
        return json.load(f)


@pytest.mark.eval
class TestEndToEndScenario:
    """P3: Full pipeline regression test using the real enrichment pipeline."""

    def test_pipeline_produces_correct_outcomes(self, tmp_path: Path) -> None:
        """Real pipeline must produce correct chunk assignments and compliance.

        Steps:
        1. Index scenario chunks into a temporary vector store
        2. Map controls to chunks via vector similarity
        3. Run the REAL ``enrich_with_rationale()`` pipeline (batch
           evaluation, batch meta-classification, gap rationale, meta
           resolution)
        4. Assert outcomes match expected
        """
        scenario = _load_scenario()

        # --- Step 1: Index chunks ---
        embedder = Embedder()
        chunks = [
            ParsedChunk(
                chunk_id=c["chunk_id"],
                document_name=c["document_name"],
                page_number=c["page_number"],
                raw_text=c["raw_text"],
                section_header=c.get("section_header"),
                embedding=embedder.embed_text(c["raw_text"]),
            )
            for c in scenario["chunks"]
        ]
        store = VectorStore(db_path=tmp_path / "e2e_eval_db")
        store.index_chunks("chunks", chunks)

        # --- Step 2: Map controls ---
        controls = [SecurityControl(**c) for c in scenario["controls"]]
        results = map_controls(
            controls=controls,
            store=store,
            collection_name="chunks",
            top_k=5,
            embedder=embedder,
        )

        # --- Step 3: Run the REAL enrichment pipeline ---
        from ctrlmap._defaults import DEFAULT_LLM_MODEL

        results = enrich_with_rationale(
            results,
            llm_model=DEFAULT_LLM_MODEL,
            concurrency=4,
            cache_enabled=False,
        )

        # --- Assert outcomes ---
        expected = scenario["expected_outcomes"]
        passed = 0
        total = len(expected)

        for result in results:
            ctrl_id = result.control.control_id
            if ctrl_id not in expected:
                continue

            exp = expected[ctrl_id]
            chunk_ids = {c.chunk_id for c in result.supporting_chunks}
            has_chunks = len(result.supporting_chunks) > 0

            # Check: has supporting chunks
            if exp["has_supporting_chunks"]:
                assert has_chunks, f"{ctrl_id}: expected supporting chunks but got none"
                # Check: expected chunk IDs are present
                for expected_id in exp["expected_relevant_chunk_ids"]:
                    assert expected_id in chunk_ids, (
                        f"{ctrl_id}: expected chunk {expected_id} not found in {chunk_ids}"
                    )

            # Check: compliance direction
            if isinstance(result.rationale, MappingRationale):
                assert result.rationale.is_compliant == exp["expected_is_compliant"], (
                    f"{ctrl_id}: expected is_compliant={exp['expected_is_compliant']}, "
                    f"got {result.rationale.is_compliant}"
                )

            passed += 1
            print(f"  [OK] {ctrl_id}: chunks={list(chunk_ids)}, compliant={result.rationale}")

        print(f"\nE2E Scenario: {passed}/{total} controls passed")
        assert passed == total, f"Only {passed}/{total} controls passed E2E scenario"
