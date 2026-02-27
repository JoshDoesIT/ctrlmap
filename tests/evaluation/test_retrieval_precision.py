"""Story #24: RAG retrieval precision evaluation (Test Spec 3).

Goal: Evaluate the embedded vector database's ability to retrieve the correct
context given a security control query.

Given: A curated golden dataset of 50 known policy text segments and their
exact corresponding NIST 800-53 Rev 5 controls as ground truth.

When: The system indexes the segments and queries the controls using the
embedded vector space.

Then: The retrieval mechanism must surface the correct target chunk within
the top-5 results (Recall@5) for at least 90% of the queries. Top-5 is used
because NIST 800-53 Rev 5 shares the identical title "Policy and Procedures"
across 13 control families, requiring a wider retrieval window.

Ref: GitHub Issue #24.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.query import query
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.models.schemas import ParsedChunk

GOLDEN_DATASET_PATH = Path(__file__).parent.parent / "fixtures" / "golden_dataset.json"
RECALL_AT_K = 5
RECALL_THRESHOLD = 0.90


def _load_golden_dataset() -> dict:
    """Load the golden dataset from the fixtures directory."""
    with GOLDEN_DATASET_PATH.open() as f:
        return json.load(f)


def _build_chunks_from_golden(dataset: dict, embedder: Embedder) -> list[ParsedChunk]:
    """Convert golden dataset segments into ParsedChunk objects with embeddings."""
    chunks = []
    for segment in dataset["segments"]:
        chunks.append(
            ParsedChunk(
                chunk_id=segment["chunk_id"],
                document_name="golden_policy.pdf",
                page_number=1,
                raw_text=segment["text"],
                section_header=f"Control {segment['control']}",
                embedding=embedder.embed_text(segment["text"]),
            )
        )
    return chunks


@pytest.mark.eval
class TestRetrievalPrecision:
    """Story #24: RAG retrieval precision evaluation."""

    def test_recall_at_5_exceeds_threshold(self, tmp_path: Path) -> None:
        """Recall@5 must be >= 0.90 across all 50 golden dataset queries.

        For each control query in the golden dataset, we check whether the
        expected chunk IDs appear in the top-5 retrieved results. A query
        is counted as a hit if at least one expected chunk is in the top-5.
        """
        dataset = _load_golden_dataset()
        embedder = Embedder()

        # Index all golden segments
        chunks = _build_chunks_from_golden(dataset, embedder)
        store = VectorStore(db_path=tmp_path / "golden_eval_db")
        store.index_chunks("chunks", chunks)

        # Evaluate each query
        hits = 0
        total = len(dataset["queries"])
        per_query_results: list[dict] = []

        for entry in dataset["queries"]:
            query_text = entry["query"]
            expected_ids = set(entry["expected_chunk_ids"])

            results = query(
                store=store,
                collection_name="chunks",
                query_text=query_text,
                top_k=RECALL_AT_K,
                embedder=embedder,
            )

            retrieved_ids = {r.chunk_id for r in results}
            is_hit = bool(expected_ids & retrieved_ids)
            if is_hit:
                hits += 1

            per_query_results.append(
                {
                    "query": query_text[:60],
                    "expected": list(expected_ids),
                    "retrieved": list(retrieved_ids),
                    "hit": is_hit,
                }
            )

        recall = hits / total if total > 0 else 0.0

        # Print detailed results for debugging
        for r in per_query_results:
            status = "HIT" if r["hit"] else "MISS"
            print(f"  [{status}] {r['query']}...")
            if not r["hit"]:
                print(f"    Expected: {r['expected']}")
                print(f"    Retrieved: {r['retrieved']}")

        print(f"\nRecall@{RECALL_AT_K}: {recall:.4f} ({hits}/{total})")
        print(f"Threshold: {RECALL_THRESHOLD}")

        assert recall >= RECALL_THRESHOLD, (
            f"Recall@{RECALL_AT_K} = {recall:.4f} is below threshold {RECALL_THRESHOLD}. "
            f"{hits}/{total} queries hit."
        )
