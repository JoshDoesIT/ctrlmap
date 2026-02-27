"""Tests for the Sentence-Transformers embedding pipeline.

TDD RED phase for Story #11.
Ref: GitHub Issue #11.
"""

from __future__ import annotations

import numpy as np
import pytest

from ctrlmap.index.embedder import Embedder


class TestEmbedder:
    """Sentence-Transformers embedding pipeline tests."""

    @pytest.fixture()
    def embedder(self) -> Embedder:
        """Create an Embedder with the default lightweight model."""
        return Embedder()

    def test_embed_text_returns_float_vector(self, embedder: Embedder) -> None:
        """Embedding a text string returns a list of floats."""
        result = embedder.embed_text("Access control policy requires MFA.")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    def test_embed_identical_text_produces_identical_vectors(self, embedder: Embedder) -> None:
        """Identical inputs produce deterministic, identical embeddings."""
        text = "Audit logging must be enabled on all production systems."
        vec_a = embedder.embed_text(text)
        vec_b = embedder.embed_text(text)
        assert vec_a == vec_b

    def test_embed_batch_returns_correct_count(self, embedder: Embedder) -> None:
        """Batch embedding returns one vector per input text."""
        texts = [
            "Implement role-based access control.",
            "All data must be encrypted at rest.",
            "Vulnerability scans run weekly.",
        ]
        results = embedder.embed_batch(texts)
        assert len(results) == 3
        assert all(isinstance(vec, list) for vec in results)
        assert all(isinstance(v, float) for vec in results for v in vec)

    def test_similar_texts_have_high_cosine_similarity(self, embedder: Embedder) -> None:
        """Semantically similar texts produce vectors with high cosine similarity."""
        vec_a = embedder.embed_text("Implement multi-factor authentication.")
        vec_b = embedder.embed_text("Require MFA for all user logins.")
        similarity = _cosine_similarity(vec_a, vec_b)
        assert similarity > 0.5

    def test_dissimilar_texts_have_low_cosine_similarity(self, embedder: Embedder) -> None:
        """Semantically unrelated texts produce vectors with low cosine similarity."""
        vec_a = embedder.embed_text("Implement multi-factor authentication.")
        vec_b = embedder.embed_text("The recipe calls for two cups of flour.")
        similarity = _cosine_similarity(vec_a, vec_b)
        assert similarity < 0.4


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    arr_a = np.array(a)
    arr_b = np.array(b)
    return float(np.dot(arr_a, arr_b) / (np.linalg.norm(arr_a) * np.linalg.norm(arr_b)))
