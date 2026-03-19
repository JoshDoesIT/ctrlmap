"""Tests for NDCG@K and MRR retrieval quality metrics.

TDD RED phase: Item 9 from the best practices improvement roadmap.
"""

from __future__ import annotations

import pytest

from tests.evaluation.conftest import compute_mrr, compute_ndcg_at_k


class TestNDCGAtK:
    """NDCG@K: Normalized Discounted Cumulative Gain."""

    def test_perfect_ranking_returns_one(self) -> None:
        """When the relevant doc is rank 1, NDCG@K = 1.0."""
        assert compute_ndcg_at_k(
            retrieved_ids=["relevant", "a", "b"],
            relevant_ids={"relevant"},
            k=3,
        ) == pytest.approx(1.0)

    def test_relevant_at_rank_2(self) -> None:
        """NDCG@K should penalize lower rank positions."""
        ndcg = compute_ndcg_at_k(
            retrieved_ids=["a", "relevant", "b"],
            relevant_ids={"relevant"},
            k=3,
        )
        assert 0.0 < ndcg < 1.0

    def test_no_relevant_doc_returns_zero(self) -> None:
        """No relevant docs retrieved → NDCG@K = 0.0."""
        assert (
            compute_ndcg_at_k(
                retrieved_ids=["a", "b", "c"],
                relevant_ids={"relevant"},
                k=3,
            )
            == 0.0
        )

    def test_empty_retrieved_returns_zero(self) -> None:
        """Empty retrieval → NDCG@K = 0.0."""
        assert (
            compute_ndcg_at_k(
                retrieved_ids=[],
                relevant_ids={"relevant"},
                k=5,
            )
            == 0.0
        )

    def test_multiple_relevant_docs(self) -> None:
        """NDCG@K with multiple relevant docs at good positions → high score."""
        ndcg = compute_ndcg_at_k(
            retrieved_ids=["r1", "a", "r2"],
            relevant_ids={"r1", "r2"},
            k=3,
        )
        assert ndcg > 0.5

    def test_k_truncates_retrieved(self) -> None:
        """Only the first K results should be considered."""
        # Relevant at position 4 with k=3 → should not count
        ndcg = compute_ndcg_at_k(
            retrieved_ids=["a", "b", "c", "relevant"],
            relevant_ids={"relevant"},
            k=3,
        )
        assert ndcg == 0.0


class TestMRR:
    """Mean Reciprocal Rank (MRR)."""

    def test_relevant_at_rank_1_returns_one(self) -> None:
        """Relevant doc at position 1 → RR = 1.0."""
        assert (
            compute_mrr(
                retrieved_ids=["relevant", "a", "b"],
                relevant_ids={"relevant"},
            )
            == 1.0
        )

    def test_relevant_at_rank_2(self) -> None:
        """Relevant doc at position 2 → RR = 0.5."""
        assert compute_mrr(
            retrieved_ids=["a", "relevant", "b"],
            relevant_ids={"relevant"},
        ) == pytest.approx(0.5)

    def test_relevant_at_rank_3(self) -> None:
        """Relevant doc at position 3 → RR = 1/3."""
        assert compute_mrr(
            retrieved_ids=["a", "b", "relevant"],
            relevant_ids={"relevant"},
        ) == pytest.approx(1.0 / 3.0)

    def test_no_relevant_returns_zero(self) -> None:
        """No relevant docs → RR = 0.0."""
        assert (
            compute_mrr(
                retrieved_ids=["a", "b", "c"],
                relevant_ids={"relevant"},
            )
            == 0.0
        )

    def test_empty_retrieved_returns_zero(self) -> None:
        """Empty retrieval → RR = 0.0."""
        assert (
            compute_mrr(
                retrieved_ids=[],
                relevant_ids={"relevant"},
            )
            == 0.0
        )
