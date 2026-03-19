"""Tests for the cross-encoder reranker.

TDD RED phase: Item 1 from the best practices improvement roadmap.
"""

from __future__ import annotations

from ctrlmap.index.query import QueryResult


class TestReranker:
    """Cross-encoder reranker re-sorts candidates by relevance."""

    def test_reranker_reorders_by_cross_encoder_score(self) -> None:
        """Relevant text should score higher than irrelevant text after reranking."""
        from ctrlmap.index.reranker import Reranker

        reranker = Reranker()
        query = "Data must be encrypted using AES-256 encryption."
        candidates = [
            QueryResult(
                chunk_id="irrelevant",
                raw_text="The cafeteria is open Monday through Friday.",
                score=0.9,  # High ANN score but irrelevant
                metadata={},
            ),
            QueryResult(
                chunk_id="relevant",
                raw_text="All data at rest must be encrypted using AES-256 encryption standards.",
                score=0.5,  # Lower ANN score but highly relevant
                metadata={},
            ),
        ]

        results = reranker.rerank(query, candidates, top_k=2)
        assert results[0].chunk_id == "relevant", (
            f"Expected 'relevant' first after reranking, got {results[0].chunk_id}"
        )

    def test_reranker_respects_top_k(self) -> None:
        """Output length should not exceed top_k."""
        from ctrlmap.index.reranker import Reranker

        reranker = Reranker()
        candidates = [
            QueryResult(chunk_id=f"c{i}", raw_text=f"Chunk {i} text.", score=0.5, metadata={})
            for i in range(5)
        ]

        results = reranker.rerank("test query", candidates, top_k=2)
        assert len(results) <= 2

    def test_reranker_handles_empty_candidates(self) -> None:
        """Empty input should return empty output."""
        from ctrlmap.index.reranker import Reranker

        reranker = Reranker()
        results = reranker.rerank("test query", [], top_k=5)
        assert results == []

    def test_reranker_preserves_metadata(self) -> None:
        """Reranked results should retain original metadata."""
        from ctrlmap.index.reranker import Reranker

        reranker = Reranker()
        candidates = [
            QueryResult(
                chunk_id="c1",
                raw_text="Access control policy.",
                score=0.5,
                metadata={"section": "AC", "page": 1},
            ),
        ]

        results = reranker.rerank("access control", candidates, top_k=1)
        assert results[0].metadata == {"section": "AC", "page": 1}
