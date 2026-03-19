"""Tests for hybrid BM25 + vector search with Reciprocal Rank Fusion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ctrlmap.index.hybrid_search import BM25Index, _tokenize, bm25_query, hybrid_query
from ctrlmap.index.query import QueryResult


class TestBM25Index:
    """Tests for BM25 index creation and querying."""

    def test_from_chunks_builds_index(self) -> None:
        """BM25Index.from_chunks() creates a searchable index."""
        index = BM25Index.from_chunks(
            chunk_ids=["c1", "c2"],
            raw_texts=["AES-256 encryption standard", "quarterly access review"],
        )
        assert len(index.chunk_ids) == 2
        assert index.bm25 is not None

    def test_empty_chunks_returns_empty_index(self) -> None:
        """Empty input creates index with no BM25 model."""
        index = BM25Index.from_chunks(chunk_ids=[], raw_texts=[])
        assert index.bm25 is None
        assert index.chunk_ids == []

    def test_bm25_query_returns_matching_chunks(self) -> None:
        """BM25 query finds chunks with matching keywords."""
        index = BM25Index.from_chunks(
            chunk_ids=["enc", "access", "wireless"],
            raw_texts=[
                "Data must be encrypted using AES-256 encryption",
                "User access reviews conducted quarterly",
                "Wireless access points must be tested quarterly",
            ],
        )
        results = bm25_query(index, "AES-256 encryption", top_k=2)

        assert len(results) >= 1
        assert results[0].chunk_id == "enc"

    def test_bm25_query_empty_index(self) -> None:
        """BM25 query on empty index returns empty list."""
        index = BM25Index.from_chunks(chunk_ids=[], raw_texts=[])
        results = bm25_query(index, "test query")
        assert results == []


class TestTokenize:
    """Tests for the tokenizer."""

    def test_tokenize_lowercases(self) -> None:
        """Tokenizer produces lowercase tokens."""
        tokens = _tokenize("AES-256 Encryption")
        assert "aes" in tokens
        assert "256" in tokens
        assert "encryption" in tokens


class TestHybridQuery:
    """Tests for RRF fusion of BM25 + vector results."""

    def test_merges_ann_and_bm25_results(self) -> None:
        """RRF fusion combines results from both search methods."""
        # Mock ANN results
        ann_results = [
            QueryResult(chunk_id="c1", raw_text="text1", score=0.9, metadata={}),
            QueryResult(chunk_id="c2", raw_text="text2", score=0.8, metadata={}),
        ]

        # BM25 index with different ranking
        index = BM25Index.from_chunks(
            chunk_ids=["c2", "c3"],
            raw_texts=["exact keyword match text2", "another keyword match"],
        )

        with patch("ctrlmap.index.hybrid_search.query_by_embedding", return_value=ann_results):
            results = hybrid_query(
                store=MagicMock(),
                collection_name="test",
                embedding=[0.1] * 384,
                query_text="keyword match",
                bm25_index=index,
                top_k=3,
            )

        # c2 appears in both lists, so should rank highest via RRF
        ids = [r.chunk_id for r in results]
        assert "c2" in ids
        assert len(results) <= 3

    def test_empty_bm25_returns_ann_only(self) -> None:
        """When BM25 has no matches, returns only ANN results."""
        ann_results = [
            QueryResult(chunk_id="c1", raw_text="text1", score=0.9, metadata={}),
        ]
        index = BM25Index.from_chunks(chunk_ids=[], raw_texts=[])

        with patch("ctrlmap.index.hybrid_search.query_by_embedding", return_value=ann_results):
            results = hybrid_query(
                store=MagicMock(),
                collection_name="test",
                embedding=[0.1] * 384,
                query_text="unmatched query",
                bm25_index=index,
                top_k=3,
            )

        assert len(results) == 1
        assert results[0].chunk_id == "c1"


class TestWeightedRRF:
    """Weighted RRF allows tuning the balance between ANN and BM25."""

    def test_default_weights_favor_bm25(self) -> None:
        """Default BM25 weight should be 0.6 (higher than ANN's 0.4)."""
        import inspect

        sig = inspect.signature(hybrid_query)
        ann_default = sig.parameters["ann_weight"].default
        bm25_default = sig.parameters["bm25_weight"].default
        assert ann_default == 0.4, f"Expected ann_weight=0.4, got {ann_default}"
        assert bm25_default == 0.6, f"Expected bm25_weight=0.6, got {bm25_default}"

    def test_equal_weights_matches_original_behavior(self) -> None:
        """ann_weight=0.5 / bm25_weight=0.5 should produce same ranking as unweighted."""
        ann_results = [
            QueryResult(chunk_id="c1", raw_text="text1", score=0.9, metadata={}),
            QueryResult(chunk_id="c2", raw_text="text2", score=0.8, metadata={}),
        ]

        index = BM25Index.from_chunks(
            chunk_ids=["c2", "c3"],
            raw_texts=["exact keyword match text2", "another keyword match"],
        )

        with patch("ctrlmap.index.hybrid_search.query_by_embedding", return_value=ann_results):
            results = hybrid_query(
                store=MagicMock(),
                collection_name="test",
                embedding=[0.1] * 384,
                query_text="keyword match",
                bm25_index=index,
                top_k=3,
                ann_weight=0.5,
                bm25_weight=0.5,
            )

        # c2 appears in both lists, so should be in the results
        ids = [r.chunk_id for r in results]
        assert "c2" in ids

    def test_high_bm25_weight_favors_bm25_only_hits(self) -> None:
        """With bm25_weight=0.9, BM25-only results should outrank ANN-only results."""
        ann_results = [
            QueryResult(chunk_id="ann_only", raw_text="semantic match", score=0.9, metadata={}),
        ]
        bm25_results = [
            QueryResult(
                chunk_id="bm25_only",
                raw_text="exact keyword match",
                score=5.0,
                metadata={},
            ),
        ]

        index = BM25Index.from_chunks(chunk_ids=[], raw_texts=[])

        with (
            patch("ctrlmap.index.hybrid_search.query_by_embedding", return_value=ann_results),
            patch("ctrlmap.index.hybrid_search.bm25_query", return_value=bm25_results),
        ):
            results = hybrid_query(
                store=MagicMock(),
                collection_name="test",
                embedding=[0.1] * 384,
                query_text="exact keyword match",
                bm25_index=index,
                top_k=3,
                ann_weight=0.1,
                bm25_weight=0.9,
            )

        ids = [r.chunk_id for r in results]
        assert ids[0] == "bm25_only", f"Expected bm25_only first, got {ids}"
